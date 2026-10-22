from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.ext import db
from app.models.user import User
from sqlalchemy import select
from datetime import datetime, timedelta
from app.models.horarios import Horario
from app.models.service import Service
from app.models.agendamento import Agendamento

agen_bp = Blueprint("agen", __name__)


@agen_bp.route("/add", methods=["POST"])
@jwt_required()
def add_agen():
    
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify(erro="O corpo precisa ser um objeto JSON"), 400
    
    
    barbeiro_id = dados.get("barbeiro_id")
    servico_id = dados.get("servico_id")
    inicio = dados.get("inicio")
    
    
    if barbeiro_id is None or servico_id is None or inicio is None:
        return jsonify(erro="barbeiro_id, servico_id e inicio são obrigatórios"), 400
    
    if (
        isinstance(barbeiro_id, bool)
        or not isinstance(barbeiro_id, int)
        or isinstance(servico_id, bool)
        or not isinstance(servico_id, int)
    ):
        return jsonify(erro="barbeiro_id e servico_id precisam ser inteiros"), 400
    
    if not isinstance(inicio, str):
        return jsonify(erro="inicio precisa ser str, no formato %Y-%m-%dT%H:%M"), 400
    
    try:
        inicio = datetime.strptime(inicio, "%Y-%m-%dT%H:%M")
    except ValueError:
        return jsonify(erro="inicio precisa estar no formato %Y-%m-%dT%H:%M"), 400
    
    
    if inicio <= datetime.now():
        return jsonify(erro="inicio precisa estar no futuro"), 400
    
    
    barbeiro = db.session.scalar(select(User).where(User.id == barbeiro_id).where(User.ativo.is_(True)).where(User.role == "BARBEIRO"))
    
    if not barbeiro:
        return jsonify(erro="Barbeiro não encontrado"), 404
    
    
    servico = db.session.scalar(select(Service).where(Service.id == servico_id).where(Service.ativo.is_(True)))
    
    if not servico:
        return jsonify(erro="Servico não encontrado"), 404
    
    fim = inicio + timedelta(minutes=servico.duracao)
    
    if inicio.date() != fim.date():
        return jsonify(erro="O agendamento precisa terminar no mesmo dia"), 400
    
    horario_cobre_intervalo = db.session.scalar(
        select(Horario)
        .where(Horario.barbeiro_id == barbeiro_id)
        .where(Horario.dia_semana == inicio.weekday())
        .where(Horario.inicio <= inicio.time())
        .where(Horario.fim >= fim.time())
    )
    
    if not horario_cobre_intervalo:
        return jsonify(erro="Horário fora do expediente"), 409
    
    conflito = db.session.scalar(
        select(Agendamento)
        .where(Agendamento.barbeiro_id == barbeiro_id)
        .where(Agendamento.status == "CONFIRMADO")
        .where(Agendamento.inicio < fim)
        .where(Agendamento.fim > inicio)
    )
     
    if conflito:
        return jsonify(erro="Barbeiro já possui agendamento nesse horário"), 409
    
    novo_agendamento = Agendamento(
        cliente_id=int(get_jwt_identity()),
        barbeiro_id=barbeiro_id,
        servico_id=servico_id,
        inicio=inicio,
        fim=fim,
        status="CONFIRMADO",
    )
    
    db.session.add(novo_agendamento)
    db.session.commit()
    
    return jsonify(msg="Agendamento criado", agendamento=novo_agendamento.to_dict()), 201


    
    
    
    
    
    
    