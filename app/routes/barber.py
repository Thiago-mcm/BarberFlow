from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app.ext import db
from app.models.user import User
from app.utils.decorators import role_required
from sqlalchemy import select
from datetime import datetime
from app.models.horarios import Horario



barber_bp = Blueprint("barber", __name__)

@barber_bp.route("/consult")
@jwt_required()
def show():
    
    barber = db.session.scalars(select(User).where(User.ativo.is_(True)).where(User.role == "BARBEIRO")).all()
    
    return jsonify([{"id": b.id, "nome": b.nome} for b in barber]), 200




@barber_bp.route("/horario", methods=["POST"])
@role_required("ADMIN")
def add_horario():
    dados = request.get_json(silent=True) or {}
    
    barbeiro_id = dados.get("barbeiro_id")
    dia_semana = dados.get("dia_semana")
    inicio = dados.get("inicio") or ""
    fim = dados.get("fim") or ""
    
    
    if not barbeiro_id or dia_semana is None or not inicio or not fim:
        return jsonify(erro="barbeiro_id, dia da semana, inicio e fim são obrigatórios"), 400
    
    
    if isinstance(barbeiro_id, bool) or not isinstance(barbeiro_id, int):
         
        return jsonify(erro="barbeiro_id precisa ser numero inteiro"), 400
     
    if isinstance(dia_semana, bool) or not isinstance(dia_semana, int):
        return jsonify(erro="dia_semana precisa ser numero inteiro"), 400
     
    
        
    
    if not 0 <= dia_semana <= 6:
        return jsonify(erro="Dia da semana tem que ser de 0 a 6"), 400
    
    
    if not isinstance(inicio, str) or not isinstance(fim, str):
        return jsonify(erro="Inicio e fim precisam ser string"), 400
    
    try:
        inicio = datetime.strptime(inicio, "%H:%M").time()
        fim = datetime.strptime(fim, "%H:%M").time()
        
    except ValueError:
        return jsonify(erro="erro ao converter as horas do inicio e fim"), 400
    
    if inicio >= fim:
        return jsonify(erro="inicio tem que ser menor que fim"), 400
    
    
    consult = db.session.scalar(select(User).where(barbeiro_id == User.id).where(User.ativo.is_(True)).where(User.role == "BARBEIRO"))
    
    if not consult:
        return jsonify(erro="barbeiro não encontrado"), 404
    
    
    conflito = db.session.scalar(
    select(Horario)
    .where(Horario.barbeiro_id == barbeiro_id)
    .where(Horario.dia_semana == dia_semana)
    .where(Horario.inicio < fim)
    .where(Horario.fim > inicio)
)

    if conflito:
        return jsonify(erro="Esse horario ja possui reserva"), 409

    
    horario_barber = Horario(
        barbeiro_id=barbeiro_id,
        dia_semana=dia_semana,
        inicio=inicio,
        fim=fim        
    )
    
    
    db.session.add(horario_barber)
    db.session.commit()
    
    return jsonify(msg="Horario criado", horario=horario_barber.to_dict()), 201



@barber_bp.route("/consult/<int:id_barbeiro>", methods=["GET"])
@jwt_required()
def listar_hr_barber(id_barbeiro):
    
    barbeiro = db.session.scalar(
    select(User)
    .where(User.id == id_barbeiro)
    .where(User.role == "BARBEIRO")
    .where(User.ativo.is_(True))
)

    if not barbeiro:
        return jsonify(erro="Barbeiro invalido"), 404

    horarios = db.session.scalars(
        select(Horario)
        .where(Horario.barbeiro_id == id_barbeiro)
        .order_by(Horario.dia_semana, Horario.inicio)
    ).all()

    return jsonify(horarios=[h.to_dict() for h in horarios]), 200


@barber_bp.route("/del/<int:id_hr>", methods=["DELETE"])
@role_required("ADMIN")
def delete_hr(id_hr):

    consult = db.session.scalar(select(Horario).where(Horario.id == id_hr))

    if not consult:
        return jsonify(erro="horario não encontrado"), 404

    db.session.delete(consult)
    db.session.commit()

    return jsonify(msg="Horario removido"), 200
    
    
    
    
        
    
    
    
    

    
    
    