from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.ext import db
from app.models.user import User
from app.utils.decorators import role_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    dados = request.get_json(silent=True) or {}

    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        return jsonify(erro="nome, email e senha são obrigatórios"), 400

    if len(senha) < 8:
        return jsonify(erro="a senha deve ter pelo menos 8 caracteres"), 400

    if User.query.filter_by(email=email).first():
        return jsonify(erro="email já cadastrado"), 409

    user = User(
        nome=nome,
        email=email,
        senha_hash=generate_password_hash(senha),
    )
    db.session.add(user)
    db.session.commit()

    return jsonify(id=user.id, nome=user.nome, email=user.email, role=user.role), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True) or {}

    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not email or not senha:
        return jsonify(erro="email e senha são obrigatórios"), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.senha_hash, senha):
        return jsonify(erro="email ou senha inválidos"), 401
    
    
    if not user.ativo:
        return jsonify(erro="Usuario desativado"), 403
    
    
    token = create_access_token(
        identity=str(user.id),
    )

    return jsonify(access_token=token), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))

    if not user or not user.ativo:
        return jsonify(erro="usuário não encontrado"), 404

    return jsonify(id=user.id, nome=user.nome, email=user.email, role=user.role), 200




@auth_bp.route("/edit/<int:id_usuario>", methods=["PATCH"])
@role_required("ADMIN")
def update_user(id_usuario):
    dados = request.get_json(silent=True)
    if not isinstance(dados, dict) or not dados:
        return jsonify(erro="envie ao menos um campo"), 400

    usuario = db.session.get(User, id_usuario)
    if not usuario or not usuario.ativo:
        return jsonify(erro="Usuário não encontrado"), 404

    
    if "nome" in dados:
        nome = dados["nome"]
        if not isinstance(nome, str) or not nome.strip():
            return jsonify(erro="nome inválido"), 400
        nome = nome.strip()
        if len(nome) > 100:
            return jsonify(erro="nome deve ter no máximo 100 caracteres"), 400

    if "email" in dados:
        email = dados["email"]
        if not isinstance(email, str) or not email.strip():
            return jsonify(erro="email inválido"), 400
        email = email.strip().lower()
        if "@" not in email or len(email) > 120:
            return jsonify(erro="email inválido"), 400

        outro = db.session.scalar(
            select(User).where(User.email == email).where(User.id != id_usuario)
        )
        if outro:
            return jsonify(erro="email já cadastrado"), 409

    
    if "nome" in dados:
        usuario.nome = nome
    if "email" in dados:
        usuario.email = email

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(erro="email já cadastrado"), 409

    return jsonify(usuario.to_dict()), 200


@auth_bp.route("/delete/<int:id_usuario>", methods=["DELETE"])
@role_required("ADMIN")
def deletar_usuario(id_usuario):
    
    consult = db.session.scalar(select(User).where(User.ativo == True).where(User.id == id_usuario))
    
    if not consult:
        return jsonify(erro="Usuario não encontrado"), 404
    
    if id_usuario == int(get_jwt_identity()):
        return jsonify(erro="Você não pode apagar a própria conta"), 400
    
    consult.ativo = False
    db.session.commit()
    
    return jsonify(msg="Usuario inativado", usuario=consult.to_dict()), 200

    

