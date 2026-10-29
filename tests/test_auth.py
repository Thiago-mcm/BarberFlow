from flask_jwt_extended import create_access_token

from app.ext import db
from app.models.user import User


# Teste 1 — listagem de agendamentos exige token.
def test_listagem_sem_token_retorna_401(client):
    resposta = client.get("/agen/list")

    assert resposta.status_code == 401


# Teste 2 — criação de agendamento exige token.
def test_criacao_sem_token_retorna_401(client):
    resposta = client.post("/agen/add", json={})

    assert resposta.status_code == 401


# Teste 3 — cliente não pode editar usuário pela rota de admin.
def test_cliente_nao_pode_editar_usuario(client, app):
    with app.app_context():
        cliente = User(
            nome="Cliente de teste",
            email="cliente@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="CLIENTE",
        )
        db.session.add(cliente)
        db.session.commit()

        token = create_access_token(identity=str(cliente.id))

    resposta = client.patch(
        f"/auth/edit/{cliente.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"nome": "Nome alterado"},
    )

    assert resposta.status_code == 403


# Teste 4 — token de usuário desativado deixa de funcionar.
def test_usuario_desativado_nao_usa_token_antigo(client, app):
    with app.app_context():
        usuario = User(
            nome="Usuário de teste",
            email="inativo@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="CLIENTE",
        )
        db.session.add(usuario)
        db.session.commit()

        token = create_access_token(identity=str(usuario.id))

        usuario.ativo = False
        db.session.commit()

    resposta = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 401


# Teste 5 — cadastro sem senha é rejeitado.
def test_cadastro_sem_senha_retorna_400(client):
    resposta = client.post(
        "/auth/register",
        json={
            "nome": "Pessoa de teste",
            "email": "pessoa@teste.com",
        },
    )

    assert resposta.status_code == 400


# Teste 6 — login sem senha é rejeitado.
def test_login_sem_senha_retorna_400(client):
    resposta = client.post(
        "/auth/login",
        json={"email": "pessoa@teste.com"},
    )

    assert resposta.status_code == 400


# Teste 7 — cadastro com senha menor que oito caracteres é rejeitado.
def test_cadastro_recusa_senha_curta(client):
    resposta = client.post(
        "/auth/register",
        json={
            "nome": "Pessoa de teste",
            "email": "curta@teste.com",
            "senha": "123",
        },
    )

    assert resposta.status_code == 400


# Teste 8 — cliente não consegue escolher a própria role no cadastro.
def test_cadastro_cria_cliente_mesmo_se_enviar_role_admin(client):
    resposta = client.post(
        "/auth/register",
        json={
            "nome": "Pessoa de teste",
            "email": "role@teste.com",
            "senha": "senha123",
            "role": "ADMIN",
        },
    )

    assert resposta.status_code == 201
    assert resposta.get_json()["role"] == "CLIENTE"


# Teste 9 — email já cadastrado retorna conflito.
def test_cadastro_recusa_email_duplicado(client):
    dados = {
        "nome": "Pessoa de teste",
        "email": "duplicado@teste.com",
        "senha": "senha123",
    }

    primeira_resposta = client.post("/auth/register", json=dados)
    segunda_resposta = client.post("/auth/register", json=dados)

    assert primeira_resposta.status_code == 201
    assert segunda_resposta.status_code == 409


# Teste 10 — senha incorreta não permite fazer login.
def test_login_com_senha_incorreta_retorna_401(client):
    client.post(
        "/auth/register",
        json={
            "nome": "Pessoa de teste",
            "email": "login-errado@teste.com",
            "senha": "senha123",
        },
    )

    resposta = client.post(
        "/auth/login",
        json={
            "email": "login-errado@teste.com",
            "senha": "senha-errada",
        },
    )

    assert resposta.status_code == 401


# Teste 11 — credenciais corretas retornam um token.
def test_login_correto_devolve_token(client):
    client.post(
        "/auth/register",
        json={
            "nome": "Pessoa de teste",
            "email": "login-certo@teste.com",
            "senha": "senha123",
        },
    )

    resposta = client.post(
        "/auth/login",
        json={
            "email": "login-certo@teste.com",
            "senha": "senha123",
        },
    )

    assert resposta.status_code == 200
    assert "access_token" in resposta.get_json()


# Teste 12 — /auth/me retorna os dados do usuário com um token válido.
def test_me_com_token_retorna_usuario(client):
    client.post(
        "/auth/register",
        json={
            "nome": "Pessoa de teste",
            "email": "me@teste.com",
            "senha": "senha123",
        },
    )

    login = client.post(
        "/auth/login",
        json={
            "email": "me@teste.com",
            "senha": "senha123",
        },
    )

    token = login.get_json()["access_token"]

    resposta = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["email"] == "me@teste.com"
# Teste 13 — cadastro rejeita JSON que não seja um objeto.
def test_cadastro_com_json_que_nao_e_objeto_retorna_400(client):
    resposta = client.post("/auth/register", json=["valor"])

    assert resposta.status_code == 400


# Teste 14 — login rejeita JSON que não seja um objeto.
def test_login_com_json_que_nao_e_objeto_retorna_400(client):
    resposta = client.post("/auth/login", json=["valor"])

    assert resposta.status_code == 400
    
# Teste 15 — cliente não pode listar usuários.
def test_cliente_nao_lista_usuarios(client, app):
    with app.app_context():
        cliente = User(
            nome="Cliente de teste",
            email="cliente-lista@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="CLIENTE",
        )
        db.session.add(cliente)
        db.session.commit()

        token = create_access_token(identity=str(cliente.id))

    resposta = client.get(
        "/auth/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 403


# Teste 16 — admin lista usuários e pode filtrar por role.
def test_admin_lista_usuarios_e_filtra_por_role(client, app):
    with app.app_context():
        admin = User(
            nome="Admin de teste",
            email="admin-lista@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="ADMIN",
        )
        barbeiro = User(
            nome="Barbeiro de teste",
            email="barbeiro-lista@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="BARBEIRO",
        )
        db.session.add_all([admin, barbeiro])
        db.session.commit()

        token = create_access_token(identity=str(admin.id))
        barbeiro_id = barbeiro.id

    todos = client.get(
        "/auth/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    so_barbeiros = client.get(
        "/auth/users?role=BARBEIRO",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert todos.status_code == 200
    assert len(todos.get_json()) == 2
    assert [u["id"] for u in so_barbeiros.get_json()] == [barbeiro_id]
    
# Teste 17 — admin promove cliente a barbeiro.
def test_admin_promove_cliente_a_barbeiro(client, app):
    with app.app_context():
        admin = User(
            nome="Admin de teste",
            email="admin-role@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="ADMIN",
        )
        cliente = User(
            nome="Cliente de teste",
            email="cliente-role@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="CLIENTE",
        )
        db.session.add_all([admin, cliente])
        db.session.commit()

        token = create_access_token(identity=str(admin.id))
        cliente_id = cliente.id

    resposta = client.patch(
        f"/auth/role/{cliente_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "BARBEIRO"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["usuario"]["role"] == "BARBEIRO"


# Teste 18 — cliente não altera role, nem a própria.
def test_cliente_nao_altera_role(client, app):
    with app.app_context():
        cliente = User(
            nome="Cliente de teste",
            email="cliente-quer-admin@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="CLIENTE",
        )
        db.session.add(cliente)
        db.session.commit()

        token = create_access_token(identity=str(cliente.id))
        cliente_id = cliente.id

    resposta = client.patch(
        f"/auth/role/{cliente_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "ADMIN"},
    )

    assert resposta.status_code == 403


# Teste 19 — role inválida retorna 400.
def test_role_invalida_retorna_400(client, app):
    with app.app_context():
        admin = User(
            nome="Admin de teste",
            email="admin-role-invalida@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="ADMIN",
        )
        alvo = User(
            nome="Alvo de teste",
            email="alvo-role@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="CLIENTE",
        )
        db.session.add_all([admin, alvo])
        db.session.commit()

        token = create_access_token(identity=str(admin.id))
        alvo_id = alvo.id

    resposta = client.patch(
        f"/auth/role/{alvo_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "DONO"},
    )

    assert resposta.status_code == 400


# Teste 20 — admin não altera a própria role.
def test_admin_nao_altera_a_propria_role(client, app):
    with app.app_context():
        admin = User(
            nome="Admin de teste",
            email="admin-propria-role@teste.com",
            senha_hash="hash-apenas-para-teste",
            role="ADMIN",
        )
        db.session.add(admin)
        db.session.commit()

        token = create_access_token(identity=str(admin.id))
        admin_id = admin.id

    resposta = client.patch(
        f"/auth/role/{admin_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"role": "CLIENTE"},
    )

    assert resposta.status_code == 400
