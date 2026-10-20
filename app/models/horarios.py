from app.ext import db

class Horario(db.Model):
    __tablename__ = "horarios"
    
    id = db.Column(db.Integer, primary_key=True)
    barbeiro_id = db.Column(db.ForeignKey("users.id"), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)
    inicio = db.Column(db.Time, nullable=False)
    fim = db.Column(db.Time, nullable=False)
    
    def to_dict(self):
        return{
            "id": self.id,
            "barbeiro_id": self.barbeiro_id,
            "dia_semana": self.dia_semana,
            "inicio": self.inicio.strftime("%H:%M"),
            "fim": self.fim.strftime("%H:%M")
        }
        