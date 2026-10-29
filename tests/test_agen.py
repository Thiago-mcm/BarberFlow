from datetime import datetime, time, timedelta
from decimal import Decimal

from flask_jwt_extended import create_access_token

from app.ext import db
from app.models.agendamento import Agendamento
from app.models.horarios import Horario
from app.models.service import Service
from app.models.user import User


def criar_usuario(app, email, role="CLIENTE"):
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
    with app.app_context():
        return create_access_token(identity=str(usuario_id))


def criar_servico(app, duracao=30):
    with app.app_context():
        servico = Service(
            nome="Serviço de teste",
            preco=Decimal("35.00"),
            duracao=duracao,
            ativo=True,
        )
        db.session.add(servico)
        db.session.commit()
        return servico.id


def criar_horario(app, barbeiro_id, dia_semana, inicio=time(9), fim=time(18)):
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


def criar_agendamento(
    app,
    cliente_id,
    barbeiro_id,
    servico_id,
    inicio,
    status="CONFIRMADO",
):
    with app.app_context():
        agendamento = Agendamento(
            cliente_id=cliente_id,
            barbeiro_id=barbeiro_id,
            servico_id=servico_id,
            inicio=inicio,
            fim=inicio + timedelta(minutes=30),
            status=status,
        )
        db.session.add(agendamento)
        db.session.commit()
        return agendamento.id


def data_futura(hora=10, minuto=0):
    dia = (datetime.now() + timedelta(days=8)).date()
    return datetime.combine(dia, time(hora, minuto))


def dados_criacao(barbeiro_id, servico_id, inicio):
    return {
        "barbeiro_id": barbeiro_id,
        "servico_id": servico_id,
        "inicio": inicio.strftime("%Y-%m-%dT%H:%M"),
    }


# Teste 1 — criar agendamento sem token retorna 401.
def test_criar_agendamento_sem_token_retorna_401(client):
    resposta = client.post("/agen/add", json={})

    assert resposta.status_code == 401


# Teste 2 — corpo incompleto com token retorna 400.
def test_criar_agendamento_sem_campos_obrigatorios_retorna_400(client, app):
    cliente_id = criar_usuario(app, "cliente-campos@teste.com")
    token = criar_token(app, cliente_id)

    resposta = client.post(
        "/agen/add",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )

    assert resposta.status_code == 400


# Teste 3 — usuário autenticado consegue criar agendamento válido.
def test_criar_agendamento_valido(client, app):
    cliente_id = criar_usuario(app, "cliente-criar@teste.com")
    barbeiro_id = criar_usuario(app, "barbeiro-criar@teste.com", role="BARBEIRO")
    servico_id = criar_servico(app)
    inicio = data_futura()
    criar_horario(app, barbeiro_id, inicio.weekday())
    token = criar_token(app, cliente_id)

    resposta = client.post(
        "/agen/add",
        headers={"Authorization": f"Bearer {token}"},
        json=dados_criacao(barbeiro_id, servico_id, inicio),
    )

    assert resposta.status_code == 201
    assert resposta.get_json()["agendamento"]["cliente_id"] == cliente_id


# Teste 4 — início fora do expediente retorna 409.
def test_criar_agendamento_fora_do_expediente_retorna_409(client, app):
    cliente_id = criar_usuario(app, "cliente-fora-horario@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-fora-horario@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = data_futura(hora=19)
    criar_horario(app, barbeiro_id, inicio.weekday())
    token = criar_token(app, cliente_id)

    resposta = client.post(
        "/agen/add",
        headers={"Authorization": f"Bearer {token}"},
        json=dados_criacao(barbeiro_id, servico_id, inicio),
    )

    assert resposta.status_code == 409


# Teste 5 — não permite criar agendamento sobre outro confirmado.
def test_criar_agendamento_em_horario_ocupado_retorna_409(client, app):
    cliente_id = criar_usuario(app, "cliente-conflito@teste.com")
    outro_cliente_id = criar_usuario(app, "outro-cliente-conflito@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-conflito-agen@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = data_futura()
    criar_horario(app, barbeiro_id, inicio.weekday())
    criar_agendamento(
        app,
        outro_cliente_id,
        barbeiro_id,
        servico_id,
        inicio,
    )
    token = criar_token(app, cliente_id)

    resposta = client.post(
        "/agen/add",
        headers={"Authorization": f"Bearer {token}"},
        json=dados_criacao(barbeiro_id, servico_id, inicio),
    )

    assert resposta.status_code == 409


# Teste 6 — cliente vê somente os próprios agendamentos confirmados, por início.
def test_cliente_lista_somente_seus_confirmados_em_ordem(client, app):
    cliente_id = criar_usuario(app, "cliente-lista-agen@teste.com")
    outro_cliente_id = criar_usuario(app, "outro-cliente-lista-agen@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-lista-agen@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    base = data_futura()
    primeiro_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        base + timedelta(hours=2),
    )
    segundo_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        base,
    )
    criar_agendamento(
        app,
        outro_cliente_id,
        barbeiro_id,
        servico_id,
        base + timedelta(hours=1),
    )
    criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        base + timedelta(hours=3),
        status="CANCELADO",
    )
    token = criar_token(app, cliente_id)

    resposta = client.get(
        "/agen/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    ids = [item["id"] for item in resposta.get_json()["agendamentos"]]

    assert resposta.status_code == 200
    assert ids == [segundo_id, primeiro_id]


# Teste 7 — barbeiro vê os agendamentos associados a ele.
def test_barbeiro_lista_seus_agendamentos(client, app):
    cliente_id = criar_usuario(app, "cliente-lista-barbeiro@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-lista-proprio@teste.com",
        role="BARBEIRO",
    )
    outro_barbeiro_id = criar_usuario(
        app,
        "outro-barbeiro-lista@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = data_futura()
    proprio_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        inicio,
    )
    criar_agendamento(
        app,
        cliente_id,
        outro_barbeiro_id,
        servico_id,
        inicio + timedelta(hours=1),
    )
    token = criar_token(app, barbeiro_id)

    resposta = client.get(
        "/agen/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    ids = [item["id"] for item in resposta.get_json()["agendamentos"]]

    assert resposta.status_code == 200
    assert ids == [proprio_id]


# Teste 8 — ADMIN vê todos os agendamentos confirmados.
def test_admin_lista_todos_os_confirmados(client, app):
    admin_id = criar_usuario(app, "admin-lista-agen@teste.com", role="ADMIN")
    cliente_id = criar_usuario(app, "cliente-admin-lista@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-admin-lista@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    base = data_futura()
    primeiro_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        base,
    )
    segundo_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        base + timedelta(hours=1),
    )
    criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        base + timedelta(hours=2),
        status="CANCELADO",
    )
    token = criar_token(app, admin_id)

    resposta = client.get(
        "/agen/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    ids = [item["id"] for item in resposta.get_json()["agendamentos"]]

    assert resposta.status_code == 200
    assert ids == [primeiro_id, segundo_id]


# Teste 9 — cliente pode cancelar seu agendamento com mais de duas horas.
def test_cliente_cancela_proprio_agendamento(client, app):
    cliente_id = criar_usuario(app, "cliente-cancela-proprio@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-cancela-proprio@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=3)
    agendamento_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        inicio,
    )
    token = criar_token(app, cliente_id)

    resposta = client.delete(
        f"/agen/del/{agendamento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["agendamento"]["status"] == "CANCELADO"


# Teste 10 — cliente não pode cancelar agendamento de outra pessoa.
def test_cliente_nao_cancela_agendamento_alheio(client, app):
    cliente_id = criar_usuario(app, "cliente-tenta-cancelar@teste.com")
    dono_id = criar_usuario(app, "dono-agendamento@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-agendamento-alheio@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=3)
    agendamento_id = criar_agendamento(
        app,
        dono_id,
        barbeiro_id,
        servico_id,
        inicio,
    )
    token = criar_token(app, cliente_id)

    resposta = client.delete(
        f"/agen/del/{agendamento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 403


# Teste 11 — cliente não pode cancelar com menos de duas horas.
def test_cliente_nao_cancela_com_menos_de_duas_horas(client, app):
    cliente_id = criar_usuario(app, "cliente-prazo@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-prazo@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
    agendamento_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        inicio,
    )
    token = criar_token(app, cliente_id)

    resposta = client.delete(
        f"/agen/del/{agendamento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 400


# Teste 12 — ADMIN pode cancelar sem respeitar o prazo de duas horas.
def test_admin_cancela_sem_limite_de_duas_horas(client, app):
    admin_id = criar_usuario(app, "admin-cancela-cedo@teste.com", role="ADMIN")
    cliente_id = criar_usuario(app, "cliente-admin-cancela@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-admin-cancela@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=1)
    agendamento_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        inicio,
    )
    token = criar_token(app, admin_id)

    resposta = client.delete(
        f"/agen/del/{agendamento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["agendamento"]["status"] == "CANCELADO"


# Teste 13 — cancelar ID inexistente retorna 404.
def test_cancelar_agendamento_inexistente_retorna_404(client, app):
    cliente_id = criar_usuario(app, "cliente-id-inexistente@teste.com")
    token = criar_token(app, cliente_id)

    resposta = client.delete(
        "/agen/del/999",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 404


# Teste 14 — cancelar agendamento já cancelado retorna 409.
def test_cancelar_agendamento_ja_cancelado_retorna_409(client, app):
    cliente_id = criar_usuario(app, "cliente-ja-cancelado@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-ja-cancelado@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=3)
    agendamento_id = criar_agendamento(
        app,
        cliente_id,
        barbeiro_id,
        servico_id,
        inicio,
        status="CANCELADO",
    )
    token = criar_token(app, cliente_id)

    resposta = client.delete(
        f"/agen/del/{agendamento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 409
    
# Teste 15 — a listagem traz os nomes de cliente, barbeiro e serviço.
def test_listagem_traz_nomes(client, app):
    cliente_id = criar_usuario(app, "cliente-nomes@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-nomes@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    criar_agendamento(app, cliente_id, barbeiro_id, servico_id, data_futura())
    token = criar_token(app, cliente_id)

    resposta = client.get(
        "/agen/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    item = resposta.get_json()["agendamentos"][0]

    assert resposta.status_code == 200
    assert item["cliente"]["nome"] == "Usuário de teste"
    assert item["barbeiro"]["id"] == barbeiro_id
    assert item["servico"]["nome"] == "Serviço de teste"
    assert item["servico"]["duracao"] == 30
    assert item["servico_id"] == servico_id

# Teste 16 — sem filtro só confirmados; com status, o histórico aparece.
def test_listagem_filtra_por_status(client, app):
    cliente_id = criar_usuario(app, "cliente-historico@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-historico@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    base = data_futura()
    confirmado_id = criar_agendamento(
        app, cliente_id, barbeiro_id, servico_id, base
    )
    cancelado_id = criar_agendamento(
        app, cliente_id, barbeiro_id, servico_id,
        base + timedelta(hours=1), status="CANCELADO",
    )
    concluido_id = criar_agendamento(
        app, cliente_id, barbeiro_id, servico_id,
        base - timedelta(days=30), status="CONCLUIDO",
    )
    token = criar_token(app, cliente_id)
    headers = {"Authorization": f"Bearer {token}"}

    def ids(url):
        resposta = client.get(url, headers=headers)
        assert resposta.status_code == 200
        return [i["id"] for i in resposta.get_json()["agendamentos"]]

    assert ids("/agen/list") == [confirmado_id]
    assert ids("/agen/list?status=CANCELADO") == [cancelado_id]
    assert ids("/agen/list?status=todos") == [concluido_id, confirmado_id, cancelado_id]

    invalido = client.get("/agen/list?status=XYZ", headers=headers)
    assert invalido.status_code == 400
    
# Teste 17 — barbeiro conclui atendimento que já começou.
def test_barbeiro_conclui_atendimento(client, app):
    cliente_id = criar_usuario(app, "cliente-conclui@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-conclui@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=1)
    agendamento_id = criar_agendamento(
        app, cliente_id, barbeiro_id, servico_id, inicio
    )
    token = criar_token(app, barbeiro_id)

    resposta = client.patch(
        f"/agen/concluir/{agendamento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 200
    assert resposta.get_json()["agendamento"]["status"] == "CONCLUIDO"


# Teste 18 — não conclui agendamento futuro.
def test_nao_conclui_agendamento_futuro(client, app):
    cliente_id = criar_usuario(app, "cliente-conclui-futuro@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-conclui-futuro@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = datetime.now().replace(second=0, microsecond=0) + timedelta(hours=3)
    agendamento_id = criar_agendamento(
        app, cliente_id, barbeiro_id, servico_id, inicio
    )
    token = criar_token(app, barbeiro_id)

    resposta = client.patch(
        f"/agen/concluir/{agendamento_id}",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resposta.status_code == 400


# Teste 19 — cliente e barbeiro de outro agendamento não concluem.
def test_cliente_e_barbeiro_alheio_nao_concluem(client, app):
    cliente_id = criar_usuario(app, "cliente-conclui-nao@teste.com")
    dono_id = criar_usuario(
        app,
        "barbeiro-dono-conclui@teste.com",
        role="BARBEIRO",
    )
    outro_id = criar_usuario(
        app,
        "barbeiro-outro-conclui@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    inicio = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=1)
    agendamento_id = criar_agendamento(
        app, cliente_id, dono_id, servico_id, inicio
    )

    resposta_cliente = client.patch(
        f"/agen/concluir/{agendamento_id}",
        headers={"Authorization": f"Bearer {criar_token(app, cliente_id)}"},
    )
    resposta_outro = client.patch(
        f"/agen/concluir/{agendamento_id}",
        headers={"Authorization": f"Bearer {criar_token(app, outro_id)}"},
    )

    assert resposta_cliente.status_code == 403
    assert resposta_outro.status_code == 403


# Teste 20 — cancelado não conclui e concluído não cancela.
def test_estados_invalidos_de_conclusao(client, app):
    admin_id = criar_usuario(app, "admin-estados@teste.com", role="ADMIN")
    cliente_id = criar_usuario(app, "cliente-estados@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-estados@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app)
    passado = datetime.now().replace(second=0, microsecond=0) - timedelta(hours=2)
    cancelado_id = criar_agendamento(
        app, cliente_id, barbeiro_id, servico_id, passado, status="CANCELADO"
    )
    concluido_id = criar_agendamento(
        app, cliente_id, barbeiro_id, servico_id,
        passado - timedelta(hours=1), status="CONCLUIDO",
    )
    headers = {"Authorization": f"Bearer {criar_token(app, admin_id)}"}

    assert client.patch(f"/agen/concluir/{cancelado_id}", headers=headers).status_code == 409
    assert client.patch(f"/agen/concluir/{concluido_id}", headers=headers).status_code == 409
    assert client.delete(f"/agen/del/{concluido_id}", headers=headers).status_code == 409
    
def cenario_disponibilidade(app, duracao=30):
    cliente_id = criar_usuario(app, "cliente-disp@teste.com")
    barbeiro_id = criar_usuario(
        app,
        "barbeiro-disp@teste.com",
        role="BARBEIRO",
    )
    servico_id = criar_servico(app, duracao=duracao)
    dia = data_futura()
    criar_horario(app, barbeiro_id, dia.weekday(), inicio=time(9), fim=time(12))
    token = criar_token(app, cliente_id)

    return cliente_id, barbeiro_id, servico_id, dia, token


def url_disponibilidade(barbeiro_id, servico_id, dia):
    return (
        f"/barber/{barbeiro_id}/disponibilidade"
        f"?data={dia.strftime('%Y-%m-%d')}&servico_id={servico_id}"
    )


# Teste 21 — lista os horários livres do expediente.
def test_disponibilidade_lista_horarios_livres(client, app):
    _, barbeiro_id, servico_id, dia, token = cenario_disponibilidade(app)

    resposta = client.get(
        url_disponibilidade(barbeiro_id, servico_id, dia),
        headers={"Authorization": f"Bearer {token}"},
    )

    horas = [h["inicio"][-5:] for h in resposta.get_json()["horarios"]]

    assert resposta.status_code == 200
    assert horas == ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30"]


# Teste 22 — horário confirmado some da lista; cancelado não.
def test_disponibilidade_remove_confirmado_e_ignora_cancelado(client, app):
    cliente_id, barbeiro_id, servico_id, dia, token = cenario_disponibilidade(app)
    criar_agendamento(app, cliente_id, barbeiro_id, servico_id, dia.replace(hour=10))
    criar_agendamento(
        app, cliente_id, barbeiro_id, servico_id,
        dia.replace(hour=11), status="CANCELADO",
    )

    resposta = client.get(
        url_disponibilidade(barbeiro_id, servico_id, dia),
        headers={"Authorization": f"Bearer {token}"},
    )

    horas = [h["inicio"][-5:] for h in resposta.get_json()["horarios"]]

    assert horas == ["09:00", "09:30", "10:30", "11:00", "11:30"]


# Teste 23 — serviço de 60 minutos só começa onde cabe inteiro.
def test_disponibilidade_respeita_duracao_do_servico(client, app):
    _, barbeiro_id, servico_id, dia, token = cenario_disponibilidade(app, duracao=60)

    resposta = client.get(
        url_disponibilidade(barbeiro_id, servico_id, dia),
        headers={"Authorization": f"Bearer {token}"},
    )

    horas = [h["inicio"][-5:] for h in resposta.get_json()["horarios"]]

    assert horas == ["09:00", "09:30", "10:00", "10:30", "11:00"]


# Teste 24 — dia sem expediente devolve lista vazia e parâmetros faltando dão 400.
def test_disponibilidade_dia_sem_expediente_e_parametros_invalidos(client, app):
    _, barbeiro_id, servico_id, dia, token = cenario_disponibilidade(app)
    headers = {"Authorization": f"Bearer {token}"}

    outro_dia = client.get(
        url_disponibilidade(barbeiro_id, servico_id, dia + timedelta(days=1)),
        headers=headers,
    )
    sem_params = client.get(f"/barber/{barbeiro_id}/disponibilidade", headers=headers)
    barbeiro_inexistente = client.get(
        url_disponibilidade(999, servico_id, dia), headers=headers
    )

    assert outro_dia.status_code == 200
    assert outro_dia.get_json()["horarios"] == []
    assert sem_params.status_code == 400
    assert barbeiro_inexistente.status_code == 404


# Teste 25 — um horário devolvido é aceito pelo agendamento.
def test_horario_devolvido_e_aceito_pelo_agendamento(client, app):
    _, barbeiro_id, servico_id, dia, token = cenario_disponibilidade(app)
    headers = {"Authorization": f"Bearer {token}"}

    livres = client.get(
        url_disponibilidade(barbeiro_id, servico_id, dia), headers=headers
    ).get_json()["horarios"]

    resposta = client.post(
        "/agen/add",
        headers=headers,
        json={
            "barbeiro_id": barbeiro_id,
            "servico_id": servico_id,
            "inicio": livres[0]["inicio"],
        },
    )

    assert resposta.status_code == 201