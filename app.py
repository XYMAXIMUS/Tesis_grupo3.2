from flask import Flask, render_template, session, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# --- DECORADOR DE AUTENTICACIÓN ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'estudiante_id' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- CONFIGURACIÓN DE LA APLICACIÓN FLASK ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "clave_secreta_produccion_ube_2026") 

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:12345678@localhost:5432/db_tesis')

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- CONFIGURACIÓN DE ARCHIVOS ---
UPLOAD_FOLDER = os.path.join("static", "img", "avatares")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- CONFIGURACIÓN DE DIFICULTADES DE JUEGOS ---
DIFICULTAD_MEMORIA = {
    'facil':    {'puntos_ganar': 10, 'xp_ganar': 5, 'penalizacion': 0},
    'normal':   {'puntos_ganar': 20, 'xp_ganar': 10, 'penalizacion': 0},
    'dificil':  {'puntos_ganar': 35, 'xp_ganar': 20, 'penalizacion': 10}
}
DIFICULTAD_TICTACTOE = {
    'facil':    {'puntos_ganar': 8,  'xp_ganar': 4, 'penalizacion': 0},
    'normal':   {'puntos_ganar': 15, 'xp_ganar': 8, 'penalizacion': 0},
    'dificil':  {'puntos_ganar': 25, 'xp_ganar': 18, 'penalizacion': 7}
}

# --- MODELOS DE LA BASE DE DATOS ---

estudiante_logros = db.Table('estudiante_logros',
    db.Column('estudiante_id', db.Integer, db.ForeignKey('estudiantes.id'), primary_key=True),
    db.Column('logro_id', db.Integer, db.ForeignKey('logros.id'), primary_key=True)
)

class Estudiante(db.Model):
    __tablename__ = 'estudiantes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    puntos = db.Column(db.Integer, default=0, nullable=False)
    xp = db.Column(db.Integer, default=0, nullable=False)
    nivel = db.Column(db.Integer, default=1, nullable=False)
    avatar_personal = db.Column(db.String(255), default='avatar-1.png')
    marco_personal = db.Column(db.String(255), default=None, nullable=True) # MODIFICADO: No asigna marco al inicio
    fondo_personal = db.Column(db.String(255), default=None, nullable=True)
    
    inventario = db.relationship('Inventario', backref='estudiante', lazy=True, cascade="all, delete-orphan")
    progreso_misiones = db.relationship('ProgresoMision', backref='estudiante', lazy=True, cascade="all, delete-orphan")
    logros = db.relationship('Logro', secondary=estudiante_logros, backref='estudiantes', lazy='dynamic')
    actividades_completadas = db.relationship('EstudianteActividadCompletada', backref='estudiante_rel', lazy='dynamic', cascade="all, delete-orphan")

class Objeto(db.Model):
    __tablename__ = 'objetos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    imagen_url = db.Column(db.String(255))
    precio = db.Column(db.Integer, nullable=False)

class Inventario(db.Model):
    __tablename__ = 'inventario'
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), nullable=False)
    objeto_id = db.Column(db.Integer, db.ForeignKey('objetos.id'), nullable=False)
    objeto = db.relationship('Objeto', backref='en_inventarios')

class Mision(db.Model):
    __tablename__ = 'misiones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(50), nullable=False, unique=True)
    action_trigger = db.Column(db.String(50), nullable=False)
    meta = db.Column(db.Integer, nullable=False)
    recompensa_puntos = db.Column(db.Integer, default=0, nullable=False)
    recompensa_xp = db.Column(db.Integer, default=0, nullable=False)

    progresos = db.relationship('ProgresoMision', backref='mision', lazy=True, cascade="all, delete-orphan")

class ProgresoMision(db.Model):
    __tablename__ = 'progreso_misiones'
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), nullable=False)
    mision_id = db.Column(db.Integer, db.ForeignKey('misiones.id'), nullable=False)
    progreso = db.Column(db.Integer, default=0, nullable=False)
    completada = db.Column(db.Boolean, default=False, nullable=False)

class Logro(db.Model):
    __tablename__ = 'logros'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    imagen_url = db.Column(db.String(255))
    nivel_requerido = db.Column(db.Integer, default=1)

class Actividad(db.Model):
    __tablename__ = 'actividades'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    puntos_recompensa = db.Column(db.Integer, default=10, nullable=False)

class EstudianteActividadCompletada(db.Model):
    __tablename__ = 'estudiante_actividades_completadas'
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), primary_key=True)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), primary_key=True)
    fecha_completado = db.Column(db.DateTime, default=db.func.current_timestamp())

    actividad = db.relationship('Actividad', backref='completada_por_estudiantes')

# --- INICIALIZACIÓN SEGURA DE LA BASE DE DATOS (MODIFICADA) ---
with app.app_context():
    db.create_all()

    # Cargar datos iniciales SOLO si la base de datos está vacía
    if Objeto.query.count() == 0:
        print("Cargando catálogos iniciales en la base de datos...")
        misiones_iniciales = [
            Mision(nombre="Primer Paso Gamer", descripcion="Juega una partida de memoria.", tipo="jugar_memoria_1", action_trigger="jugar_memoria", meta=1, recompensa_puntos=10, recompensa_xp=5),
            Mision(nombre="Veterano de Memoria", descripcion="Juega 5 partidas de memoria.", tipo="jugar_memoria_5", action_trigger="jugar_memoria", meta=5, recompensa_puntos=50, recompensa_xp=30),
            Mision(nombre="Victoria Memoriosa", descripcion="Gana una partida de memoria.", tipo="ganar_memoria_1", action_trigger="ganar_memoria", meta=1, recompensa_puntos=30, recompensa_xp=15),
            Mision(nombre="Tic-Tac-Experto", descripcion="Juega una partida de Tic-Tac-Toe.", tipo="jugar_tictactoe_1", action_trigger="jugar_tictactoe", meta=1, recompensa_puntos=10, recompensa_xp=5),
            Mision(nombre="Dominador del Tres en Raya", descripcion="Gana una partida de Tic-Tac-Toe.", tipo="ganar_tictactoe_1", action_trigger="ganar_tictactoe", meta=1, recompensa_puntos=25, recompensa_xp=12),
            Mision(nombre="Maestro del Tres en Raya", descripcion="Gana 3 partidas de Tic-Tac-Toe.", tipo="ganar_tictactoe_3", action_trigger="ganar_tictactoe", meta=3, recompensa_puntos=75, recompensa_xp=40),
            Mision(nombre="El Coleccionista", descripcion="Compra un marco en la tienda.", tipo="comprar_marco_1", action_trigger="comprar_marco", meta=1, recompensa_puntos=20, recompensa_xp=10),
            Mision(nombre="Gastador Inteligente", descripcion="Gasta un total de 100 puntos en la tienda.", tipo="gastar_puntos_100", action_trigger="gastar_puntos", meta=100, recompensa_puntos=50, recompensa_xp=25),
            Mision(nombre="Nueva Apariencia", descripcion="Cambia tu avatar en ajustes.", tipo="cambiar_avatar_1", action_trigger="cambiar_avatar", meta=1, recompensa_puntos=15, recompensa_xp=8),
        ]
        db.session.add_all(misiones_iniciales)

        objetos_iniciales = [
            Objeto(nombre="Avatar Gamer 2", tipo="avatar", descripcion="Un avatar moderno para tu perfil.", imagen_url="avatares/avatar-2.png", precio=50),
            Objeto(nombre="Avatar Gamer 3", tipo="avatar", descripcion="Muestra tu estilo competitivo.", imagen_url="avatares/avatar-3.png", precio=75),
            Objeto(nombre="Marco Amarillo", tipo="marco", descripcion="Marco brillante color amarillo.", imagen_url="marcos/marco_amarillo.png", precio=50),
            Objeto(nombre="Marco Azul", tipo="marco", descripcion="Marco brillante de tono azul.", imagen_url="marcos/marco_azul.png", precio=100),
            Objeto(nombre="Marco Celeste", tipo="marco", descripcion="Marco fresco color celeste.", imagen_url="marcos/marco_celeste.png", precio=80),
            Objeto(nombre="Marco Morado", tipo="marco", descripcion="Marco elegante de color morado.", imagen_url="marcos/marco_morado.png", precio=120),
            Objeto(nombre="Marco Rojo", tipo="marco", descripcion="Marco intenso de color rojo.", imagen_url="marcos/marco_rojo.png", precio=100),
            Objeto(nombre="Marco Verde", tipo="marco", descripcion="Marco natural color verde.", imagen_url="marcos/marco_verde.png", precio=90),
            Objeto(nombre="Fondo Bosque", tipo="fondo", descripcion="Un sereno fondo natural.", imagen_url="fondos/bosque.png", precio=150),
            Objeto(nombre="Fondo Cielo", tipo="fondo", descripcion="Un hermoso fondo del cielo.", imagen_url="fondos/cielo.png", precio=150),
            Objeto(nombre="Fondo Ciudad", tipo="fondo", descripcion="Fondo urbano nocturno.", imagen_url="fondos/city.jpg", precio=180)
        ]
        db.session.add_all(objetos_iniciales)

        logros_iniciales = [
            Logro(nombre="Primer Paso", descripcion="Realiza tu primera compra en la tienda.", imagen_url="medallas/Medalla_Primer_Compra.png", nivel_requerido=1),
            Logro(nombre="Explorador", descripcion="Juega diversas partidas en la plataforma.", imagen_url="medallas/Medalla_Explorador_de_Juegos.png", nivel_requerido=1),
            Logro(nombre="Maestro de Memoria", descripcion="Demuestra tus habilidades de memoria.", imagen_url="medallas/Medalla_Maestro_de_Memoria.png", nivel_requerido=2),
            Logro(nombre="Constancia Semanal", descripcion="Mantén tu actividad constante en la plataforma.", imagen_url="medallas/Medalla_Constancia_Semanal.png", nivel_requerido=3),
        ]
        db.session.add_all(logros_iniciales)

        actividades_iniciales = [
            Actividad(nombre="Lectura de Artículo", descripcion="Lee un artículo científico sobre IA.", puntos_recompensa=10),
            Actividad(nombre="Participación en Foro", descripcion="Publica una pregunta o respuesta en el foro del curso.", puntos_recompensa=10),
            Actividad(nombre="Asistencia a Webinar", descripcion="Asiste a un webinar de la UBE.", puntos_recompensa=10),
            Actividad(nombre="Entrega de Tarea Extra", descripcion="Entrega una tarea opcional para puntos extra.", puntos_recompensa=10),
        ]
        db.session.add_all(actividades_iniciales)

        db.session.commit()
        print("¡Base de datos cargada correctamente!")

# --- FUNCIONES AUXILIARES DE GAMIFICACIÓN ---

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calcular_xp_para_siguiente_nivel(nivel_actual):
    return nivel_actual * 100

def verificar_y_actualizar_nivel(estudiante):
    xp_necesaria_para_siguiente_nivel = calcular_xp_para_siguiente_nivel(estudiante.nivel)
    while estudiante.xp >= xp_necesaria_para_siguiente_nivel:
        estudiante.nivel += 1
        flash(f"🎉 ¡Felicidades! Has alcanzado el **Nivel {estudiante.nivel}** 🎉", "info")
        xp_necesaria_para_siguiente_nivel = calcular_xp_para_siguiente_nivel(estudiante.nivel)
        verificar_y_asignar_logros(estudiante)

def verificar_y_asignar_logros(estudiante):
    logros_disponibles = Logro.query.filter(
        Logro.nivel_requerido <= estudiante.nivel,
        ~Logro.estudiantes.any(id=estudiante.id)
    ).all()

    for logro in logros_disponibles:
        estudiante.logros.append(logro)
        flash(f"🏆 ¡Has desbloqueado un nuevo logro: '{logro.nombre}'! 🏆", "success")

def procesar_accion_gamificada(estudiante_id, action_trigger, cantidad=1):
    estudiante = db.session.get(Estudiante, estudiante_id) 
    if not estudiante:
        return

    misiones_a_actualizar = Mision.query.filter_by(action_trigger=action_trigger).all()
    if not misiones_a_actualizar:
        return

    for mision in misiones_a_actualizar:
        progreso = ProgresoMision.query.filter_by(
            estudiante_id=estudiante.id,
            mision_id=mision.id
        ).first()
        
        if not progreso:
            progreso = ProgresoMision(estudiante_id=estudiante.id, mision_id=mision.id, progreso=0, completada=False)
            db.session.add(progreso)
        
        if progreso.progreso is None:
            progreso.progreso = 0

        if not progreso.completada:
            progreso.progreso += cantidad
            if progreso.progreso >= mision.meta:
                progreso.completada = True
                estudiante.puntos += mision.recompensa_puntos
                estudiante.xp += mision.recompensa_xp
                flash(f"✨ ¡Misión completada: '{mision.nombre}'! Has ganado {mision.recompensa_puntos} puntos y {mision.recompensa_xp} XP. ✨", "success")
                verificar_y_actualizar_nivel(estudiante)
                verificar_y_asignar_logros(estudiante)

# --- RUTAS DE LA APLICACIÓN ---

@app.route("/")
@login_required 
def index():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    xp_necesaria_total_para_siguiente_nivel = calcular_xp_para_siguiente_nivel(estudiante.nivel)
    xp_actual_en_nivel = estudiante.xp - calcular_xp_para_siguiente_nivel(estudiante.nivel - 1) if estudiante.nivel > 1 else estudiante.xp
    xp_restante_para_siguiente_nivel = xp_necesaria_total_para_siguiente_nivel - estudiante.xp
    
    xp_actual_en_nivel = max(0, xp_actual_en_nivel)
    progreso_xp = (xp_actual_en_nivel / 100) * 100 if xp_necesaria_total_para_siguiente_nivel > 0 else 0

    misiones_activas_db = ProgresoMision.query.filter_by(
        estudiante_id=estudiante.id,
        completada=False
    ).limit(3).all() 

    misiones_rapidas = []
    for progreso_mision in misiones_activas_db:
        mision_obj = progreso_mision.mision
        misiones_rapidas.append({
            'id': mision_obj.id,
            'nombre': mision_obj.nombre,
            'descripcion': mision_obj.descripcion,
            'tipo': mision_obj.tipo,
            'meta': mision_obj.meta,
            'recompensa_puntos': mision_obj.recompensa_puntos,
            'recompensa_xp': mision_obj.recompensa_xp,
            'progreso_actual': progreso_mision.progreso,
            'completada': progreso_mision.completada
        })

    return render_template('index.html',
        estudiante=estudiante, 
        nivel=estudiante.nivel,
        progreso_xp=progreso_xp,
        xp_actual=estudiante.xp,
        xp_siguiente_nivel_total=xp_necesaria_total_para_siguiente_nivel,
        xp_restante_para_siguiente_nivel=max(0, xp_restante_para_siguiente_nivel),
        activo='panel',
        misiones_rapidas=misiones_rapidas
    )

@app.route("/tienda")
@login_required
def tienda():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    objetos = Objeto.query.all()
    inventario_ids = {item.objeto_id for item in estudiante.inventario}
    
    return render_template("tienda.html", 
        objetos=objetos, 
        inventario_ids=inventario_ids, 
        estudiante=estudiante,
        activo='tienda',
        avatar=estudiante.avatar_personal, 
        marco=estudiante.marco_personal, 
        name=estudiante.nombre
    )

@app.route("/comprar/<int:obj_id>")
@login_required
def comprar(obj_id):
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    objeto = db.session.get(Objeto, obj_id)

    if not objeto:
        flash("El objeto no existe.", "danger")
        return redirect(url_for('tienda'))

    if estudiante.puntos < objeto.precio:
        flash("No tienes suficientes puntos para comprar este objeto.", "danger")
        return redirect(url_for('tienda'))

    if objeto.id in {item.objeto_id for item in estudiante.inventario}:
        flash("Ya tienes este objeto en tu inventario.", "warning")
        return redirect(url_for('tienda'))
    
    estudiante.puntos -= objeto.precio
    nuevo_item = Inventario(estudiante_id=estudiante.id, objeto_id=objeto.id)
    db.session.add(nuevo_item)
    
    if objeto.tipo == 'marco':
        procesar_accion_gamificada(estudiante.id, 'comprar_marco')
    procesar_accion_gamificada(estudiante.id, 'gastar_puntos', objeto.precio)

    db.session.commit()
    flash("¡Compra realizada con éxito!", "success")
    return redirect(url_for('tienda'))

@app.route("/inventario")
@login_required
def inventario():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    return render_template("inventario.html", 
        inventario=estudiante.inventario, 
        activo='inventario',
        estudiante=estudiante,
        avatar=estudiante.avatar_personal, 
        marco=estudiante.marco_personal, 
        name=estudiante.nombre
    )

@app.route("/equipar/<string:tipo>/<int:obj_id>")
@login_required
def equipar(tipo, obj_id):
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    item_inventario = Inventario.query.filter_by(estudiante_id=estudiante.id, objeto_id=obj_id).first()

    if not item_inventario or item_inventario.objeto.tipo != tipo:
        flash("No puedes equipar este objeto.", "danger")
        return redirect(url_for('inventario'))

    imagen = os.path.basename(item_inventario.objeto.imagen_url)

    if tipo == 'avatar':
        estudiante.avatar_personal = imagen
        procesar_accion_gamificada(estudiante.id, 'cambiar_avatar')
    elif tipo == 'marco':
        estudiante.marco_personal = imagen
    elif tipo == 'fondo':
        estudiante.fondo_personal = imagen

    db.session.commit()
    flash("¡Objeto equipado con éxito!", "success")
    return redirect(url_for('inventario'))

@app.route("/ranking")
@login_required
def ranking():
    estudiante_actual = db.session.get(Estudiante, session['estudiante_id'])
    ranking_estudiantes = Estudiante.query.order_by(Estudiante.puntos.desc(), Estudiante.xp.desc()).all()

    return render_template("ranking.html", 
        ranking=ranking_estudiantes, 
        activo='ranking',
        estudiante=estudiante_actual,
        avatar=estudiante_actual.avatar_personal, 
        marco=estudiante_actual.marco_personal, 
        name=estudiante_actual.nombre
    )

@app.route('/misiones')
@login_required
def mostrar_misiones():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    misiones_db = Mision.query.all() 

    misiones_con_progreso = []
    for mision_obj in misiones_db: 
        progreso = ProgresoMision.query.filter_by(
            estudiante_id=estudiante.id,
            mision_id=mision_obj.id
        ).first()

        progreso_actual = progreso.progreso if progreso else 0
        completada = progreso.completada if progreso else False

        misiones_con_progreso.append({
            'id': mision_obj.id,
            'nombre': mision_obj.nombre,
            'descripcion': mision_obj.descripcion,
            'tipo': mision_obj.tipo,
            'action_trigger': mision_obj.action_trigger,
            'meta': mision_obj.meta,
            'recompensa_puntos': mision_obj.recompensa_puntos,
            'recompensa_xp': mision_obj.recompensa_xp,
            'progreso_actual': progreso_actual,
            'completada': completada
        })

    return render_template('misiones.html', misiones=misiones_con_progreso, estudiante=estudiante)

@app.route('/logros')
@login_required
def mostrar_logros():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    return render_template('logros.html', 
                           estudiante=estudiante, 
                           logros_obtenidos=estudiante.logros.all(), 
                           activo='logros' 
                          )

@app.route('/completar_actividad/<int:actividad_id>')
@login_required
def completar_actividad(actividad_id):
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    actividad = db.session.get(Actividad, actividad_id)

    if not estudiante:
        flash("Sesión no válida. Por favor, inicia sesión.", "danger")
        return redirect(url_for('login'))
    
    if not actividad:
        flash("Actividad no encontrada.", "danger")
        return redirect(url_for('mostrar_historial_actividades'))

    actividad_ya_completada = db.session.get(EstudianteActividadCompletada, (estudiante.id, actividad.id))

    if actividad_ya_completada:
        flash(f"Ya has completado la actividad '{actividad.nombre}'.", "info")
        return redirect(url_for('mostrar_historial_actividades'))

    nueva_actividad_completada = EstudianteActividadCompletada(
        estudiante_id=estudiante.id,
        actividad_id=actividad.id
    )
    db.session.add(nueva_actividad_completada)
    estudiante.puntos += actividad.puntos_recompensa

    verificar_y_actualizar_nivel(estudiante)
    verificar_y_asignar_logros(estudiante)

    try:
        db.session.commit()
        flash(f"¡Has completado la actividad '{actividad.nombre}' y ganado {actividad.puntos_recompensa} puntos!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al completar actividad: {e}", "danger")
    
    return redirect(url_for('mostrar_historial_actividades'))

@app.route('/historial_actividades')
@login_required
def mostrar_historial_actividades():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    historial = estudiante.actividades_completadas.order_by(EstudianteActividadCompletada.fecha_completado.desc()).all()

    return render_template('historial_actividades.html', 
                           estudiante=estudiante, 
                           historial=historial,
                           activo='historial_actividades'
                          )

@app.route("/ajustes", methods=["GET", "POST"])
@login_required
def ajustes():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    if not estudiante:
        flash("Sesión no válida. Por favor, inicia sesión.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        nuevo_nombre = request.form.get("nombre")
        if nuevo_nombre and 3 <= len(nuevo_nombre) <= 30 and nuevo_nombre != estudiante.nombre:
            nombre_antiguo = estudiante.nombre
            estudiante.nombre = nuevo_nombre
            try:
                db.session.commit()
                flash("Nombre cambiado correctamente.", "success")
            except IntegrityError:
                db.session.rollback()
                estudiante.nombre = nombre_antiguo
                flash(f"El nombre '{nuevo_nombre}' ya está en uso. Por favor, elige otro.", "danger")
        
        if "avatar" in request.files:
            file = request.files["avatar"]
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"user_{estudiante.id}_{file.filename}")
                path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                try:
                    file.save(path)
                    estudiante.avatar_personal = filename
                    db.session.commit()
                    flash("Avatar actualizado correctamente.", "success")
                    procesar_accion_gamificada(estudiante.id, 'cambiar_avatar')
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error al subir avatar: {e}", "danger")
            else:
                flash("Formato de archivo de avatar no permitido o archivo no seleccionado.", "warning")

        return redirect(url_for("ajustes"))

    return render_template("ajustes.html", 
        estudiante=estudiante, 
        activo='ajustes'
    )

@app.route("/resetear_progreso")
@login_required
def resetear_progreso():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    if not estudiante:
        flash("Sesión no válida. Por favor, inicia sesión.", "danger")
        return redirect(url_for('login'))

    estudiante.puntos = 0
    estudiante.xp = 0
    estudiante.nivel = 1
    estudiante.avatar_personal = 'avatar-1.png'
    estudiante.marco_personal = None
    estudiante.fondo_personal = None
    
    Inventario.query.filter_by(estudiante_id=estudiante.id).delete()
    ProgresoMision.query.filter_by(estudiante_id=estudiante.id).delete()
    estudiante.logros = []
    EstudianteActividadCompletada.query.filter_by(estudiante_id=estudiante.id).delete()

    db.session.commit()
    flash("¡Tu progreso ha sido reiniciado! ¡Empieza de nuevo!", "info")
    return redirect(url_for("index"))

@app.route("/juegos")
@login_required
def juegos():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    return render_template("juegos.html", 
        activo='juegos',
        estudiante=estudiante,
        avatar=estudiante.avatar_personal, 
        marco=estudiante.marco_personal, 
        name=estudiante.nombre
    )

@app.route("/juego/memoria")
@login_required
def memoria():
    dificultad = request.args.get('dificultad', 'normal')
    config = DIFICULTAD_MEMORIA.get(dificultad, DIFICULTAD_MEMORIA['normal'])
    estudiante = db.session.get(Estudiante, session['estudiante_id'])

    return render_template("memoria.html", 
        activo='juegos',
        dificultad=dificultad,
        puntos_ganar=config['puntos_ganar'],
        xp_ganar=config['xp_ganar'],
        penalizacion=config['penalizacion'],
        estudiante=estudiante,
        avatar=estudiante.avatar_personal, 
        marco=estudiante.marco_personal, 
        name=estudiante.nombre
    )

@app.route("/juego/tictactoe/menu")
@login_required
def tictactoe_volver_menu():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    return render_template("tictactoe_menu.html", 
        activo='juegos',
        avatar=estudiante.avatar_personal, 
        marco=estudiante.marco_personal, 
        name=estudiante.nombre
    )

@app.route("/juego/tictactoe/ganar", methods=["POST"])
@login_required
def tictactoe_ganar():
    return jsonify({"status": "deprecated", "message": "Por favor, usa /juego/resultado"}), 400

@app.route("/juego/tictactoe/perder", methods=["POST"])
@login_required
def tictactoe_perder():
    return jsonify({"status": "deprecated", "message": "Por favor, usa /juego/resultado"}), 400

@app.route("/juego/tictactoe")
@login_required
def tictactoe():
    modo = request.args.get('modo', 'bot')
    dificultad = request.args.get('dificultad', 'normal')
    config = DIFICULTAD_TICTACTOE.get(dificultad, DIFICULTAD_TICTACTOE['normal'])
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    
    return render_template("tictactoe.html", 
        activo='juegos',
        modo=modo,
        dificultad=dificultad,
        puntos_ganar=config['puntos_ganar'],
        xp_ganar=config['xp_ganar'],
        penalizacion=config['penalizacion'],
        estudiante=estudiante,
        avatar=estudiante.avatar_personal, 
        marco=estudiante.marco_personal, 
        name=estudiante.nombre
    )

@app.route("/juego/resultado", methods=["POST"])
@login_required
def juego_resultado():
    data = request.get_json()
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    
    juego = data.get('juego')
    resultado = data.get('resultado')
    dificultad = data.get('dificultad', 'normal')

    if not all([juego, resultado, estudiante]):
        return jsonify({"status": "error", "message": "Datos incompletos para procesar el resultado del juego."}), 400

    if juego == 'memoria':
        procesar_accion_gamificada(estudiante.id, 'jugar_memoria') 
        if resultado == 'ganado':
            procesar_accion_gamificada(estudiante.id, 'ganar_memoria')

    elif juego == 'tictactoe':
        procesar_accion_gamificada(estudiante.id, 'jugar_tictactoe')
        config = DIFICULTAD_TICTACTOE.get(dificultad, DIFICULTAD_TICTACTOE['normal'])
        if resultado == 'ganado':
            procesar_accion_gamificada(estudiante.id, 'ganar_tictactoe')
        elif resultado == 'perdido':
            estudiante.puntos = max(0, estudiante.puntos - config['penalizacion']) 
        elif resultado == 'empatado':
            pass 
    
    verificar_y_actualizar_nivel(estudiante)
    verificar_y_asignar_logros(estudiante)

    try:
        db.session.commit()
        return jsonify({"status": "ok", "nuevos_puntos": estudiante.puntos, "nuevos_xp": estudiante.xp, "nuevo_nivel": estudiante.nivel})
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar el resultado del juego: {e}")
        return jsonify({"status": "error", "message": "Error al guardar el progreso del juego."}), 500

@app.context_processor
def inject_user_data():
    if 'estudiante_id' not in session:
        return {} 
    
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    if not estudiante:
        session.pop('estudiante_id', None)
        return {}
    
    misiones_activas_count = sum(1 for p in estudiante.progreso_misiones if not p.completada)
        
    return dict(
        name=estudiante.nombre,
        avatar=estudiante.avatar_personal,
        marco=estudiante.marco_personal,
        misiones_sidebar=[p for p in estudiante.progreso_misiones if not p.completada],
        misiones_activas_count=misiones_activas_count
    )

# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')

        if not nombre or not email or not password:
            flash('Por favor, completa todos los campos.', 'danger')
            return redirect(url_for('registro'))
        if len(nombre) < 3 or len(nombre) > 30:
            flash('El nombre de usuario debe tener entre 3 y 30 caracteres.', 'danger')
            return redirect(url_for('registro'))
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return redirect(url_for('registro'))

        if Estudiante.query.filter_by(email=email).first():
            flash('El email ya está registrado.', 'danger')
            return redirect(url_for('registro'))
        if Estudiante.query.filter_by(nombre=nombre).first():
            flash('El nombre de usuario ya existe. Por favor, elige otro.', 'danger')
            return redirect(url_for('registro'))

        password_hash = generate_password_hash(password)
        nuevo_estudiante = Estudiante(nombre=nombre, email=email, password_hash=password_hash)
        
        try:
            db.session.add(nuevo_estudiante)
            db.session.commit()
            
            flash('¡Cuenta creada con éxito! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Hubo un error al registrar. El nombre de usuario o email podrían estar ya en uso.', 'danger')
            return redirect(url_for('registro'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ocurrió un error inesperado al registrar: {e}', "danger")
            return redirect(url_for('registro'))
    
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        estudiante = Estudiante.query.filter_by(email=email).first()

        if estudiante and check_password_hash(estudiante.password_hash, password):
            session['estudiante_id'] = estudiante.id
            flash(f'¡Bienvenido de nuevo, {estudiante.nombre}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email o contraseña incorrectos.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.pop('estudiante_id', None)
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

# --- PUNTO DE INICIO ---
if __name__ == "__main__":
    app.run(debug=True)
