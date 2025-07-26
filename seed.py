# Al inicio de seed.py
from app import app, db, Estudiante, Objeto, Mision, ProgresoMision, Logro, Juego

# Dentro de with app.app_context():
    # ...
    juegos_a_crear = [
        Juego(nombre='Memoria', emoji='🧠', endpoint='memoria'),
        Juego(nombre='Tic Tac Toe', emoji='❌⭕', endpoint='tictactoe_volver_menu')
    ]
    db.session.add_all(juegos_a_crear)
    # ...