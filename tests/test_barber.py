from datetime import time

from flask_jwt_extended import create_access_token

from app.ext import db
from app.models.horarios import Horario
from app.models.user import User


def criar_usuario(app, email, nome="Usuário de teste", role="CLIENTE", ativo=True):
    with app.app_context():
        usuario = User(
            nome=nome,
            email=email,
            senha_hash="hash-apenas-para-teste",
            role=role,
            ativo=ativo,
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario.id


def criar_token(app, usuario_id):
    with app.app_context():
        return create_access_token(identity=str(usuario_id))


def criar_horario(app, barbeiro_id, dia_semana=0, inicio=time(9), fim=time(17)):
    with app.app_context():
        horario = Horario(
            barbeiro_id=barbeiro_id,
            dia_semana=dia_semana,
            inicio=inicio,
            fim=fim,
        )
        db.session.add(horario)
        db.session.commit()
        return horario.id


# Teste 1 — listar barbeiros sem token deve retornar 401.
def test_listar_barbeiros_sem_token_retorna_401(client):
    resposta = client.get("/barber/consult")

    assert resposta.status_code == 401


# Teste 2 — consultar horários sem token deve retornar 401.
def test_consultar_horarios_sem_token_retorna_401(client):
    resposta = client.get("/barber/consult/1")

    assert resposta.status_code == 401


# Teste 3 — cadastrar horário sem token deve retornar 401.
def test_cadastrar_horario_sem_token_retorna_401(client):
    resposta = client.post(
        "/barber/horario",
        json={
            "barbeiro_id": 1,
            "dia_semana": 0,
            "inicio": "09:00",
            "fim": "17:00",
        },
    )

    assert resposta.status_code == 401


# Teste 4 — CLIENTE autenticado não pode cadastrar horário.
def test_cliente_nao_pode_cadastrar_horario(client, app):
    cliente_id = criar_usuario(app, "cliente-horario@teste.com")
    token = criar_token(app, cliente_id)

    resposta = client.post(
        "/barber/horario",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "barbeiro_id": 1,
            "dia_semana": 0,
            "inicio": "09:00",
            "fim": "17:00",
        },
    )

    assert resposta.status_code == 403


# Teste 5 — ADMIN pode cadastrar horário para um barbeiro ativo.
def test_admin_cadastra_horario(client, app):
    admin_id = criar_usuario(app, "admin-horario@teste.com", role="ADMIN")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-horario@teste.com",
        nome="Barbeiro de teste",
        role="BARBEIRO",
    )
    token = criar_token(app, admin_id)

    resposta = client.post(
        "/barber/horario",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "barbeiro_id": barbeiro_id,
            "dia_semana": 0,
            "inicio": "09:00",
            "fim": "17:00",
        },
    )

    assert resposta.status_code == 201
    assert resposta.get_json()["horario"]["barbeiro_id"] == barbeiro_id


# Teste 6 — horários que se sobrepõem para o mesmo barbeiro retornam 409.
def test_admin_nao_cadastra_horario_sobreposto(client, app):
    admin_id = criar_usuario(app, "admin-conflito@teste.com", role="ADMIN")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-conflito@teste.com",
        role="BARBEIRO",
    )
    token = criar_token(app, admin_id)
    headers = {"Authorization": f"Bearer {token}"}

    primeiro = client.post(
        "/barber/horario",
        headers=headers,
        json={
            "barbeiro_id": barbeiro_id,
            "dia_semana": 0,
            "inicio": "09:00",
            "fim": "12:00",
        },
    )
    segundo = client.post(
        "/barber/horario",
        headers=headers,
        json={
            "barbeiro_id": barbeiro_id,
            "dia_semana": 0,
            "inicio": "11:00",
            "fim": "13:00",
        },
    )

    assert primeiro.status_code == 201
    assert segundo.status_code == 409


# Teste 7 — a consulta lista barbeiros ativos e não mostra inativos.
def test_listar_barbeiros_mostra_apenas_ativos(client, app):
    cliente_id = criar_usuario(app, "cliente-lista-barber@teste.com")
    ativo_id = criar_usuario(
        app,
        "barbeiro-ativo@teste.com",
        nome="Barbeiro ativo",
        role="BARBEIRO",
    )
    criar_usuario(
        app,
        "barbeiro-inativo@teste.com",
        nome="Barbeiro inativo",
        role="BARBEIRO",
        ativo=False,
    )
    token = criar_token(app, cliente_id)

    resposta = client.get(
        "/barber/consult",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json() == [{"id": ativo_id, "nome": "Barbeiro ativo"}]


# Teste 8 — consultar horários de um barbeiro ativo retorna seus horários.
def test_consultar_horarios_do_barbeiro(client, app):
    cliente_id = criar_usuario(app, "cliente-consulta-barber@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-consulta@teste.com",
        role="BARBEIRO",
    )
    criar_horario(
        app,
        barbeiro_id,
        dia_semana=0,
        inicio=time(9, 0),
        fim=time(12, 0),
    )
    token = criar_token(app, cliente_id)

    resposta = client.get(
        f"/barber/consult/{barbeiro_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["horarios"][0]["inicio"] == "09:00"


# Teste 9 — ADMIN pode remover um horário existente.
def test_admin_remove_horario(client, app):
    admin_id = criar_usuario(app, "admin-remove-horario@teste.com", role="ADMIN")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-remove-horario@teste.com",
        role="BARBEIRO",
    )
    horario_id = criar_horario(app, barbeiro_id)
    token = criar_token(app, admin_id)

    resposta = client.delete(
        f"/barber/del/{horario_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200


# Teste 10 — tentar consultar horários de quem não é barbeiro retorna 404.
def test_consultar_horarios_de_usuario_que_nao_e_barbeiro_retorna_404(
    client, app
):
    cliente_id = criar_usuario(app, "cliente-nao-barbeiro@teste.com")
    token = criar_token(app, cliente_id)

    resposta = client.get(
        f"/barber/consult/{cliente_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 404

# Teste 11 — ADMIN recebe 400 quando envia JSON que não é um objeto.
def test_admin_nao_cadastra_horario_com_json_que_nao_e_objeto_retorna_400(
    client, app
):
    admin_id = criar_usuario(app, "admin-horario-json@teste.com", role="ADMIN")
    token = criar_token(app, admin_id)

    resposta = client.post(
        "/barber/horario",
        headers={"Authorization": f"Bearer {token}"},
        json=["valor"],
    )

    assert resposta.status_code == 400
