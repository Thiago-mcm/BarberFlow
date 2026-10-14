from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from sqlalchemy import select
from app.ext import db
from app.models.service import Service
from app.utils.decorators import role_required
from sqlalchemy.exc import IntegrityError

serv_bp = Blueprint("serv", __name__)


@serv_bp.route("/consult", methods=["GET"])
@jwt_required()
def lista():
    consulta = (
        select(Service)
        .where(Service.ativo.is_(True))
        .order_by(Service.nome)
    )
    resultado = db.session.scalars(consulta).all()

    return jsonify([i.to_dict() for i in resultado]), 200


@serv_bp.route("/consult/<int:servico_id>", methods=["GET"])
@jwt_required()
def listar_servico(servico_id):
   
        
    consult = select(Service).where(Service.ativo == True).where(Service.id == servico_id)    
        
    resultado = db.session.scalar(consult)
    
    if not resultado:
        return jsonify(erro="Serviço não encontrado"), 404
    
        
    return jsonify(resultado.to_dict()), 200
    

@serv_bp.route("/add", methods=["POST"])
@role_required("ADMIN")
def create():
    dados = request.get_json(silent=True) or {}

    nome = dados.get("nome")
    preco = dados.get("preco") or ""
    duracao = dados.get("duracao") or ""

    if not isinstance(nome, str) or not nome.strip() or not preco or not duracao:
        return jsonify(erro="nome, preço e duração são obrigatórios"), 400

    nome = nome.strip()

    if len(nome) > 100:
        return jsonify(erro="nome deve ter no máximo 100 caracteres"), 400

    if isinstance(duracao, bool) or not isinstance(duracao, int) or duracao <= 0:
        return jsonify(erro="duracao deve ser um inteiro maior que zero"), 400

    try:
        preco = Decimal(str(preco))
    except InvalidOperation:
        return jsonify(erro="preco deve ser um número"), 400

    if not preco.is_finite() or preco <= 0 or preco >= 100000:
        return jsonify(erro="preco deve ser maior que zero e menor que 100000"), 400

    if Service.query.filter_by(nome=nome).first():
        return jsonify(erro="serviço já cadastrado"), 409

    novo = Service(nome=nome, preco=preco, duracao=duracao)

    db.session.add(novo)
    db.session.commit()

    return jsonify(novo.to_dict()), 201

@serv_bp.route("/delete/<int:id_serv>", methods=["DELETE"])
@role_required("ADMIN")
def delete_serv(id_serv):
    
    consult = select(Service).where(Service.ativo == True).where(Service.id == id_serv)
    result = db.session.scalar(consult)
    
    if not result:
        return jsonify(erro="Serviço não encontrado"), 404
    
    
    result.ativo = False
    db.session.commit()
    
    return jsonify(msg="Serviço inativado", servico=result.to_dict()), 200





@serv_bp.route("/edit/<int:id_serv>", methods=["PATCH"])
@role_required("ADMIN")
def update_serv(id_serv):
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict) or not dados:
        return jsonify(erro="envie ao menos um campo"), 400
    
    if not any(campo in dados for campo in ("nome", "preco", "duracao")):
        return jsonify(erro="envie nome, preco ou duracao"), 400
    
    servico = db.session.get(Service, id_serv)
    
    if not servico or not servico.ativo:
        return jsonify(erro="Serviço não encontrado"), 404
    
    if "nome" in dados:
        nome = dados["nome"]
        if not isinstance(nome, str) or not nome.strip():
            return jsonify(erro="nome inválido"), 400
        nome = nome.strip()
        if len(nome) > 100:
            return jsonify(erro="nome deve ter no máximo 100 caracteres"), 400
        
        outro = db.session.scalar(select(Service).where(Service.nome == nome).where(Service.id != id_serv))
        
        if outro:
            return jsonify(erro="nome ja cadastrado"), 409
    
    if "preco" in dados:
        preco = dados["preco"]
        
        
        try:
           preco = Decimal(str(preco))
        except InvalidOperation:
            return jsonify(erro="preco deve ser um número"), 400
        
        if not preco.is_finite() or preco <= 0 or preco >= 100000:
            return jsonify(erro="preco deve ser maior que zero e menor que 100000"), 400
    
    if "duracao" in dados:
        duracao = dados["duracao"]
        
        if isinstance(duracao, bool) or not isinstance(duracao, int) or duracao <= 0:
            return jsonify(erro="duracao deve ser um inteiro maior que zero"), 400
            
    if "nome" in dados:
        servico.nome = nome
    
    
    if "preco" in dados:
        servico.preco = preco
    
    
    if "duracao" in dados:
        servico.duracao = duracao
    
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(erro="Serviço ja cadastrado"), 409  
    
    return jsonify(servico.to_dict()), 200  
            