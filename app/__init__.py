import os
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask
from app.ext import db, jwt
from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.serv import serv_bp
from app.routes.barber import barber_bp
from app.routes.agen import agen_bp

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DB_URI")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

    db.init_app(app)
    jwt.init_app(app)

    from app.models import user, service, horarios, agendamento

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(serv_bp, url_prefix="/serv")
    app.register_blueprint(barber_bp, url_prefix="/barber")
    app. register_blueprint(agen_bp, url_prefix="/agen")

    return app