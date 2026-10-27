from decimal import Decimal

from flask_jwt_extended import create_access_token

from app.ext import db
from app.models.service import Service
from app.models.user import User


def criar_usuario(app, email, role="CLIENTE"):
    """Cria um usuário de teste e devolve seu ID."""
    with app.app_context():
        usuario = User(
            nome="Usuário de teste",
            email=email,
            senha_hash="hash-apenas-para-teste",
            role=role,
        )
        db.session.add(usuario)
        db.session.commit()

        return usuario.id


def criar_token(app, usuario_id):
    """Gera um token JWT para o ID recebido."""
    with app.app_context():
        return create_access_token(identity=str(usuario_id))


def criar_servico(app, nome="Corte", ativo=True):
    """Cria um serviço de teste e devolve seu ID."""
    with app.app_context():
        servico = Service(
            nome=nome,
            preco=Decimal("35.00"),
            duracao=30,
            ativo=ativo,
        )
        db.session.add(servico)
        db.session.commit()

        return servico.id


# Teste 1 — a listagem exige autenticação.
def test_listagem_servicos_sem_token_retorna_401(client):
    resposta = client.get("/serv/consult")

    assert resposta.status_code == 401


# Teste 2 — a consulta de um serviço específico também exige autenticação.
def test_consulta_servico_sem_token_retorna_401(client):
    resposta = client.get("/serv/consult/1")

    assert resposta.status_code == 401


# Teste 3 — a criação exige autenticação.
def test_criar_servico_sem_token_retorna_401(client):
    resposta = client.post(
        "/serv/add",
        json={"nome": "Corte", "preco": 35, "duracao": 30},
    )

    assert resposta.status_code == 401


# Teste 4 — usuário CLIENTE autenticado não pode criar serviço.
def test_cliente_nao_pode_criar_servico(client, app):
    cliente_id = criar_usuario(app, "cliente-servico@teste.com")
    token = criar_token(app, cliente_id)

    resposta = client.post(
        "/serv/add",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "Corte", "preco": 35, "duracao": 30},
    )

    assert resposta.status_code == 403


# Teste 5 — ADMIN pode criar um serviço com dados válidos.
def test_admin_cria_servico(client, app):
    admin_id = criar_usuario(app, "admin-servico@teste.com", role="ADMIN")
    token = criar_token(app, admin_id)

    resposta = client.post(
        "/serv/add",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "Corte", "preco": 35, "duracao": 30},
    )

    assert resposta.status_code == 201
    assert resposta.get_json()["nome"] == "Corte"


# Teste 6 — duração inválida é rejeitada.
def test_admin_nao_cria_servico_com_duracao_invalida(client, app):
    admin_id = criar_usuario(app, "admin-duracao@teste.com", role="ADMIN")
    token = criar_token(app, admin_id)

    resposta = client.post(
        "/serv/add",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "Corte", "preco": 35, "duracao": "30"},
    )

    assert resposta.status_code == 400


# Teste 7 — o sistema não permite cadastrar dois serviços com o mesmo nome.
def test_admin_nao_cria_servico_com_nome_duplicado(client, app):
    admin_id = criar_usuario(app, "admin-duplicado@teste.com", role="ADMIN")
    token = criar_token(app, admin_id)
    headers = {"Authorization": f"Bearer {token}"}
    dados = {"nome": "Corte", "preco": 35, "duracao": 30}

    primeira_resposta = client.post("/serv/add", headers=headers, json=dados)
    segunda_resposta = client.post("/serv/add", headers=headers, json=dados)

    assert primeira_resposta.status_code == 201
    assert segunda_resposta.status_code == 409


# Teste 8 — a listagem mostra serviços ativos em ordem alfabética.
def test_listagem_mostra_servicos_ativos_em_ordem(client, app):
    cliente_id = criar_usuario(app, "cliente-lista@teste.com")
    token = criar_token(app, cliente_id)

    criar_servico(app, nome="Corte")
    criar_servico(app, nome="Barba")
    criar_servico(app, nome="Serviço inativo", ativo=False)

    resposta = client.get(
        "/serv/consult",
        headers={"Authorization": f"Bearer {token}"},
    )

    nomes = [servico["nome"] for servico in resposta.get_json()]

    assert resposta.status_code == 200
    assert nomes == ["Barba", "Corte"]


# Teste 9 — usuário autenticado consegue consultar um serviço ativo.
def test_consulta_servico_existente(client, app):
    cliente_id = criar_usuario(app, "cliente-consulta@teste.com")
    token = criar_token(app, cliente_id)
    servico_id = criar_servico(app, nome="Barba")

    resposta = client.get(
        f"/serv/consult/{servico_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["nome"] == "Barba"


# Teste 10 — serviço inexistente retorna 404.
def test_consulta_servico_inexistente_retorna_404(client, app):
    cliente_id = criar_usuario(app, "cliente-inexistente@teste.com")
    token = criar_token(app, cliente_id)

    resposta = client.get(
        "/serv/consult/999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 404


# Teste 11 — ADMIN pode editar um serviço.
def test_admin_edita_servico(client, app):
    admin_id = criar_usuario(app, "admin-edita@teste.com", role="ADMIN")
    token = criar_token(app, admin_id)
    servico_id = criar_servico(app, nome="Corte")

    resposta = client.patch(
        f"/serv/edit/{servico_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "Corte atualizado"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["nome"] == "Corte atualizado"


# Teste 12 — preço inválido é rejeitado na edição.
def test_admin_nao_edita_servico_com_preco_invalido(client, app):
    admin_id = criar_usuario(app, "admin-preco@teste.com", role="ADMIN")
    token = criar_token(app, admin_id)
    servico_id = criar_servico(app, nome="Corte")

    resposta = client.patch(
        f"/serv/edit/{servico_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"preco": 0},
    )

    assert resposta.status_code == 400


# Teste 13 — ADMIN pode desativar um serviço.
def test_admin_desativa_servico(client, app):
    admin_id = criar_usuario(app, "admin-desativa@teste.com", role="ADMIN")
    token = criar_token(app, admin_id)
    servico_id = criar_servico(app, nome="Corte")

    resposta = client.delete(
        f"/serv/delete/{servico_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["servico"]["ativo"] is False

# Teste 14 — ADMIN recebe 400 quando envia JSON que não é um objeto.
def test_admin_nao_cria_servico_com_json_que_nao_e_objeto_retorna_400(client, app):
    admin_id = criar_usuario(app, "admin-json-invalido@teste.com", role="ADMIN")
    token = criar_token(app, admin_id)

    resposta = client.post(
        "/serv/add",
        headers={"Authorization": f"Bearer {token}"},
        json=["valor"],
    )

    assert resposta.status_code == 400
