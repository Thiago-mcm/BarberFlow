from app.ext import db


class Agendamento(db.Model):
    __tablename__  = "agendamentos"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.ForeignKey("users.id"), nullable=False)
    barbeiro_id = db.Column(db.ForeignKey("users.id"), nullable=False)
    servico_id = db.Column(db.ForeignKey("services.id"), nullable=False)
    inicio = db.Column(db.DateTime, nullable=False)
    fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="CONFIRMADO")

    cliente = db.relationship("User", foreign_keys=[cliente_id], lazy="joined")
    barbeiro = db.relationship("User", foreign_keys=[barbeiro_id], lazy="joined")
    servico = db.relationship("Service", foreign_keys=[servico_id], lazy="joined")

    def to_dict(self):
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "barbeiro_id": self.barbeiro_id,
            "servico_id": self.servico_id,
            "cliente": {"id": self.cliente_id, "nome": self.cliente.nome},
            "barbeiro": {"id": self.barbeiro_id, "nome": self.barbeiro.nome},
            "servico": {
                "id": self.servico_id,
                "nome": self.servico.nome,
                "preco": float(self.servico.preco),
                "duracao": self.servico.duracao,
            },
            "inicio": self.inicio.strftime("%Y-%m-%dT%H:%M"),
            "fim": self.fim.strftime("%Y-%m-%dT%H:%M"),
            "status": self.status,
        }