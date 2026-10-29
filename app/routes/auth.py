from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.ext import db
from app.models.user import User
from app.utils.decorators import role_required
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from app.models.agendamento import Agendamento


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify(erro="O corpo precisa ser um objeto JSON"), 400

    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        return jsonify(erro="nome, email e senha são obrigatórios"), 400

    if len(senha) < 8:
        return jsonify(erro="a senha deve ter pelo menos 8 caracteres"), 400

    if db.session.scalar(select(User).where(User.email == email)):
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
    dados = request.get_json(silent=True)
    
    if not isinstance(dados, dict):
        return jsonify(erro="O corpo precisa ser um objeto JSON"), 400
    
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not email or not senha:
        return jsonify(erro="email e senha são obrigatórios"), 400

    user = db.session.scalar(select(User).where(User.email == email))

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



@auth_bp.route("/users", methods=["GET"])
@role_required("ADMIN")
def listar_usuarios():
    consulta = select(User).where(User.ativo.is_(True)).order_by(User.nome)

    role = request.args.get("role")

    if role is not None:
        role = role.strip().upper()

        if role not in ("CLIENTE", "BARBEIRO", "ADMIN"):
            return jsonify(erro="role deve ser CLIENTE, BARBEIRO ou ADMIN"), 400

        consulta = consulta.where(User.role == role)

    usuarios = db.session.scalars(consulta).all()

    return jsonify([u.to_dict() for u in usuarios]), 200




@auth_bp.route("/role/<int:id_usuario>", methods=["PATCH"])
@role_required("ADMIN")
def alterar_role(id_usuario):
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify(erro="O corpo precisa ser um objeto JSON"), 400

    role = dados.get("role")

    if not isinstance(role, str) or role.strip().upper() not in ("CLIENTE", "BARBEIRO", "ADMIN"):
        return jsonify(erro="role deve ser CLIENTE, BARBEIRO ou ADMIN"), 400

    role = role.strip().upper()

    usuario = db.session.get(User, id_usuario)

    if not usuario or not usuario.ativo:
        return jsonify(erro="Usuário não encontrado"), 404

    if id_usuario == int(get_jwt_identity()):
        return jsonify(erro="Você não pode alterar a própria role"), 400

    if usuario.role == role:
        return jsonify(msg="Role já era essa", usuario=usuario.to_dict()), 200

    if usuario.role == "BARBEIRO":
        pendente = db.session.scalar(
            select(Agendamento)
            .where(Agendamento.barbeiro_id == id_usuario)
            .where(Agendamento.status == "CONFIRMADO")
            .where(Agendamento.fim > datetime.now())
        )

        if pendente:
            return jsonify(erro="O barbeiro tem agendamentos futuros; cancele-os antes de mudar a role"), 409

    usuario.role = role
    db.session.commit()

    return jsonify(msg="Role alterada", usuario=usuario.to_dict()), 200

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
