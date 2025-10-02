from app import app
from models import db, User

with app.app_context():
    db.create_all()
    # Cria usuário inicial
    if not User.query.filter_by(username="parceiro").first():
        user = User(username="parceiro")
        user.set_password("123456")
        db.session.add(user)
        db.session.commit()
    print("Banco criado e usuário parceiro/123456 adicionado")
