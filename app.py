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
# ¡IMPORTANTE! Cambia esta clave secreta por una generada aleatoriamente y guárdala de forma segura (ej. en variables de entorno)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "una_clave_secreta_super_segura_y_aleatoria_para_produccion_12345") 

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:12345678@localhost:5432/db_tesis'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Para silenciar un warning de SQLAlchemy

# Inicializa la extensión de SQLAlchemy
db = SQLAlchemy(app)

# --- CONFIGURACIÓN DE ARCHIVOS ---
UPLOAD_FOLDER = os.path.join("static", "img", "avatares")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Asegura que la carpeta de subida exista

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

# Tabla intermedia para la relación muchos-a-muchos entre Estudiante y Logro
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
    marco_personal = db.Column(db.String(255), default='marco-1.png')
    fondo_personal = db.Column(db.String(255)) # Puede ser None si no tiene uno
    
    inventario = db.relationship('Inventario', backref='estudiante', lazy=True, cascade="all, delete-orphan")
    progreso_misiones = db.relationship('ProgresoMision', backref='estudiante', lazy=True, cascade="all, delete-orphan")
    logros = db.relationship('Logro', secondary=estudiante_logros, backref='estudiantes', lazy='dynamic')
    # RESTAURADO: Relación a las actividades completadas por el estudiante
    actividades_completadas = db.relationship('EstudianteActividadCompletada', backref='estudiante_rel', lazy='dynamic', cascade="all, delete-orphan")


class Objeto(db.Model):
    __tablename__ = 'objetos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False) # 'avatar', 'marco', 'fondo'
    descripcion = db.Column(db.Text)
    imagen_url = db.Column(db.String(255))
    precio = db.Column(db.Integer, nullable=False)

class Inventario(db.Model):
    __tablename__ = 'inventario'
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), nullable=False)
    objeto_id = db.Column(db.Integer, db.ForeignKey('objetos.id'), nullable=False)
    objeto = db.relationship('Objeto', backref='en_inventarios') # Relaciona con la tabla Objeto

class Mision(db.Model):
    __tablename__ = 'misiones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    tipo = db.Column(db.String(50), nullable=False, unique=True) # El tipo debe ser único para identificar la misión
    action_trigger = db.Column(db.String(50), nullable=False) # Disparador de acción genérico
    meta = db.Column(db.Integer, nullable=False)
    recompensa_puntos = db.Column(db.Integer, default=0, nullable=False)
    recompensa_xp = db.Column(db.Integer, default=0, nullable=False)

    progresos = db.relationship('ProgresoMision', backref='mision', lazy=True, cascade="all, delete-orphan")

class ProgresoMision(db.Model):
    __tablename__ = 'progreso_misiones'
    id = db.Column(db.Integer, primary_key=True)
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), nullable=False)
    mision_id = db.Column(db.Integer, db.ForeignKey('misiones.id'), nullable=False) # Esta es la CLAVE FORÁNEA
    progreso = db.Column(db.Integer, default=0, nullable=False)
    completada = db.Column(db.Boolean, default=False, nullable=False)
    # ELIMINADA: mision = db.relationship('Mision')

class Logro(db.Model):
    __tablename__ = 'logros'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    imagen_url = db.Column(db.String(255))
    nivel_requerido = db.Column(db.Integer, default=1)

# MODELO: Actividad (Define las actividades que existen y sus puntos)
class Actividad(db.Model):
    __tablename__ = 'actividades'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    puntos_recompensa = db.Column(db.Integer, default=10, nullable=False) # 10 puntos por defecto

# RESTAURADO: Modelo para registrar actividades completadas por estudiante (el historial)
class EstudianteActividadCompletada(db.Model):
    __tablename__ = 'estudiante_actividades_completadas'
    estudiante_id = db.Column(db.Integer, db.ForeignKey('estudiantes.id'), primary_key=True)
    actividad_id = db.Column(db.Integer, db.ForeignKey('actividades.id'), primary_key=True)
    fecha_completado = db.Column(db.DateTime, default=db.func.current_timestamp())

    actividad = db.relationship('Actividad', backref='completada_por_estudiantes')


# --- FUNCIONES AUXILIARES DE GAMIFICACIÓN ---

def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def calcular_xp_para_siguiente_nivel(nivel_actual):
    """
    Calcula la cantidad total de XP necesaria para alcanzar el nivel actual.
    Puedes ajustar esta fórmula para hacer la subida de nivel más rápida o más lenta.
    Ej: Nivel 1: 0 XP
        Nivel 2: 100 XP (necesitas 100 para pasar de 1 a 2)
        Nivel 3: 200 XP (necesitas 100 más para pasar de 2 a 3)
        Nivel N: (N-1) * 100 XP
    """
    return nivel_actual * 100 # Necesitas 100 XP para el Nivel 2, 200 XP para el Nivel 3, etc.

def verificar_y_actualizar_nivel(estudiante):
    """
    Verifica si el estudiante ha ganado suficiente XP para subir de nivel
    y actualiza su nivel en la base de datos.
    """
    xp_necesaria_para_siguiente_nivel = calcular_xp_para_siguiente_nivel(estudiante.nivel)

    # Si la XP actual del estudiante es mayor o igual a la XP necesaria para SU SIGUIENTE nivel
    # Y el nivel actual del estudiante NO coincide con el nivel que debería tener por XP (para evitar bucles infinitos si la XP baja por alguna razón)
    while estudiante.xp >= xp_necesaria_para_siguiente_nivel:
        estudiante.nivel += 1
        flash(f"🎉 ¡Felicidades! Has alcanzado el **Nivel {estudiante.nivel}** 🎉", "info")
        
        # Recalcula la XP necesaria para el nuevo siguiente nivel
        xp_necesaria_para_siguiente_nivel = calcular_xp_para_siguiente_nivel(estudiante.nivel)
        
        # Después de subir de nivel, verifica si hay logros nuevos
        verificar_y_asignar_logros(estudiante)
    
    # db.session.commit() se realizará en la ruta que llama a esta función

def verificar_y_asignar_logros(estudiante):
    """
    Asigna logros al estudiante si cumple con los requisitos de nivel
    y aún no tiene el logro.
    """
    # Busca todos los logros cuyo nivel requerido es menor o igual al nivel actual del estudiante
    # Y que el estudiante aún no tenga (usando `~Logro.estudiantes.any(id=estudiante.id)`)
    logros_disponibles = Logro.query.filter(
        Logro.nivel_requerido <= estudiante.nivel,
        ~Logro.estudiantes.any(id=estudiante.id)
    ).all()

    for logro in logros_disponibles:
        estudiante.logros.append(logro) # Añade el logro al estudiante
        flash(f"🏆 ¡Has desbloqueado un nuevo logro: '{logro.nombre}'! 🏆", "success")
    
    # db.session.commit() se realizará en la ruta que llama a esta función

def procesar_accion_gamificada(estudiante_id, action_trigger, cantidad=1):
    """
    Procesa una acción gamificada (ej. 'jugar_memoria', 'comprar_marco')
    y actualiza el progreso de TODAS las misiones asociadas a ese action_trigger.
    """
    estudiante = db.session.get(Estudiante, estudiante_id) 
    if not estudiante:
        print(f"Advertencia: Estudiante con ID {estudiante_id} no encontrado.")
        return

    # Buscar TODAS las misiones que se activan con este action_trigger
    misiones_a_actualizar = Mision.query.filter_by(action_trigger=action_trigger).all()
    
    if not misiones_a_actualizar:
        print(f"Advertencia: No se encontraron misiones para el action_trigger '{action_trigger}'")
        return

    for mision in misiones_a_actualizar:
        progreso = ProgresoMision.query.filter_by(
            estudiante_id=estudiante.id,
            mision_id=mision.id
        ).first()
        
        if not progreso:
            # Si no existe progreso para esta misión, creamos un nuevo registro
            progreso = ProgresoMision(estudiante_id=estudiante.id, mision_id=mision.id, progreso=0, completada=False)
            db.session.add(progreso)
        
        if progreso.progreso is None: # Doble verificación
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

    # El db.session.commit() se hará al final de la ruta que llamó a esta función.
    
# --- RUTAS DE LA APLICACIÓN ---

@app.route("/")
@login_required 
def index():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])

    # Cálculo de XP para el siguiente nivel de forma dinámica
    xp_necesaria_total_para_siguiente_nivel = calcular_xp_para_siguiente_nivel(estudiante.nivel)
    xp_actual_en_nivel = estudiante.xp - calcular_xp_para_siguiente_nivel(estudiante.nivel - 1) if estudiante.nivel > 1 else estudiante.xp
    xp_restante_para_siguiente_nivel = xp_necesaria_total_para_siguiente_nivel - estudiante.xp
    
    # Asegúrate de que no muestre XP negativa o progreso más allá del 100% para el nivel actual
    xp_actual_en_nivel = max(0, xp_actual_en_nivel)
    progreso_xp = (xp_actual_en_nivel / 100) * 100 if xp_necesaria_total_para_siguiente_nivel > 0 else 0

    # --- Lógica para Misiones Rápidas en el Panel ---
    misiones_activas_db = ProgresoMision.query.filter_by(
        estudiante_id=estudiante.id,
        completada=False
    ).limit(3).all() 

    misiones_rapidas = []
    for progreso_mision in misiones_activas_db:
        mision_obj = progreso_mision.mision # Accede al objeto Mision a través de la relación
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
    # --- Fin Lógica para Misiones Rápidas ---


    return render_template('index.html',
        estudiante=estudiante, 
        nivel=estudiante.nivel, # Usamos el nivel de la DB
        progreso_xp=progreso_xp,
        xp_actual=estudiante.xp, # XP total del estudiante
        xp_siguiente_nivel_total=xp_necesaria_total_para_siguiente_nivel, # XP total para el prox nivel
        xp_restante_para_siguiente_nivel=max(0, xp_restante_para_siguiente_nivel), # XP que le falta al estudiante para el prox nivel
        activo='panel',
        misiones_rapidas=misiones_rapidas # Pasa la nueva variable al template
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
    objeto = Objeto.query.get(obj_id)

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
    
    # Lógica para misiones de compra
    if objeto.tipo == 'marco':
        procesar_accion_gamificada(estudiante.id, 'comprar_marco') # Usando procesar_accion_gamificada
    procesar_accion_gamificada(estudiante.id, 'gastar_puntos', objeto.precio) # Usando procesar_accion_gamificada

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

    # os.path.basename se asegura de guardar solo el nombre del archivo
    imagen = os.path.basename(item_inventario.objeto.imagen_url)

    if tipo == 'avatar':
        estudiante.avatar_personal = imagen
        procesar_accion_gamificada(estudiante.id, 'cambiar_avatar') # Usando procesar_accion_gamificada
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
    estudiante_actual = db.session.get(Estudiante, session['estudiante_id']) # Renombrado para evitar conflicto con 'estudiante' pasado al template

    # Ordenar por puntos y luego por XP para desempates
    ranking_estudiantes = Estudiante.query.order_by(Estudiante.puntos.desc(), Estudiante.xp.desc()).all()

    # --- DEBUGGING PRINTS ---
    print("\n--- DEBUGGING RANKING ---")
    print(f"Estudiante actual ID: {estudiante_actual.id}, Nombre: {estudiante_actual.nombre}")
    print("Datos de ranking obtenidos de la DB:")
    if ranking_estudiantes:
        for i, user in enumerate(ranking_estudiantes):
            print(f"  {i+1}. Nombre: {user.nombre}, Puntos: {user.puntos}, XP: {user.xp}")
    else:
        print("  La lista de ranking_estudiantes está vacía.")
    print("--- FIN DEBUGGING RANKING ---\n")
    # --- FIN DEBUGGING PRINTS ---

    return render_template("ranking.html", 
        ranking=ranking_estudiantes, 
        activo='ranking',
        estudiante=estudiante_actual, # Usar el nombre de variable corregido
        avatar=estudiante_actual.avatar_personal, 
        marco=estudiante_actual.marco_personal, 
        name=estudiante_actual.nombre
    )
# --- RUTA PARA MISIONES ---
@app.route('/misiones')
@login_required # Si solo los usuarios logueados pueden ver las misiones
def mostrar_misiones():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])

    # Obtener TODAS las misiones de la base de datos
    misiones_db = Mision.query.all() 

    # Para cada misión, obtener el progreso del estudiante actual
    misiones_con_progreso = []
    for mision_obj in misiones_db: 
        progreso = ProgresoMision.query.filter_by(
            estudiante_id=estudiante.id,
            mision_id=mision_obj.id
        ).first()

        # Si no hay progreso para esta misión, asumimos 0 y no completada
        progreso_actual = progreso.progreso if progreso else 0
        completada = progreso.completada if progreso else False

        misiones_con_progreso.append({
            'id': mision_obj.id,
            'nombre': mision_obj.nombre,
            'descripcion': mision_obj.descripcion,
            'tipo': mision_obj.tipo,
            'action_trigger': mision_obj.action_trigger, # Asegúrate de pasar el action_trigger también
            'meta': mision_obj.meta,
            'recompensa_puntos': mision_obj.recompensa_puntos,
            'recompensa_xp': mision_obj.recompensa_xp,
            'progreso_actual': progreso_actual,
            'completada': completada
        })

    return render_template('misiones.html', misiones=misiones_con_progreso, estudiante=estudiante)

# --- RUTA PARA LOGROS ---
@app.route('/logros')
@login_required
def mostrar_logros():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    
    return render_template('logros.html', 
                           estudiante=estudiante, 
                           logros_obtenidos=estudiante.logros.all(), 
                           activo='logros' 
                          )

# --- RUTA PARA COMPLETAR ACTIVIDADES ---
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
        return redirect(url_for('mostrar_historial_actividades')) # Redirige al historial

    # Verificar si el estudiante ya completó esta actividad
    actividad_ya_completada = db.session.get(EstudianteActividadCompletada, (estudiante.id, actividad.id))

    if actividad_ya_completada:
        flash(f"Ya has completado la actividad '{actividad.nombre}'.", "info")
        return redirect(url_for('mostrar_historial_actividades')) # Redirige al historial

    # Registrar la actividad como completada
    nueva_actividad_completada = EstudianteActividadCompletada(
        estudiante_id=estudiante.id,
        actividad_id=actividad.id
    )
    db.session.add(nueva_actividad_completada)

    # Sumar puntos al estudiante
    estudiante.puntos += actividad.puntos_recompensa
    
    # Opcional: Dar XP por actividad si no está ligada a una misión
    # estudiante.xp += 5 # Ejemplo: 5 XP fija por actividad

    # Verificar nivel y logros después de sumar puntos/XP
    verificar_y_actualizar_nivel(estudiante)
    verificar_y_asignar_logros(estudiante)

    try:
        db.session.commit()
        flash(f"¡Has completado la actividad '{actividad.nombre}' y ganado {actividad.puntos_recompensa} puntos!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error al completar actividad: {e}", "danger")
    
    return redirect(url_for('mostrar_historial_actividades')) # Redirige al historial


# --- NUEVA RUTA PARA MOSTRAR HISTORIAL DE ACTIVIDADES ---
@app.route('/historial_actividades')
@login_required
def mostrar_historial_actividades():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    
    # Las actividades completadas del estudiante ya están disponibles
    # a través de la relación estudiante.actividades_completadas
    # Puedes ordenarlas por fecha si lo deseas
    historial = estudiante.actividades_completadas.order_by(EstudianteActividadCompletada.fecha_completado.desc()).all()

    return render_template('historial_actividades.html', 
                           estudiante=estudiante, 
                           historial=historial,
                           activo='historial_actividades' # Para marcar el enlace activo en la barra lateral
                          )

@app.route("/ajustes", methods=["GET", "POST"])
@login_required # Proteger ruta de ajustes
def ajustes():
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    if not estudiante:
        flash("Sesión no válida. Por favor, inicia sesión.", "danger")
        return redirect(url_for('login'))

    if request.method == "POST":
        # --- Lógica para cambiar nombre ---
        nuevo_nombre = request.form.get("nombre")
        if nuevo_nombre and 3 <= len(nuevo_nombre) <= 30 and nuevo_nombre != estudiante.nombre:
            nombre_antiguo = estudiante.nombre # Guardamos por si hay error
            estudiante.nombre = nuevo_nombre
            try:
                db.session.commit()
                flash("Nombre cambiado correctamente.", "success")
            except IntegrityError:
                db.session.rollback() # Revertimos el cambio
                estudiante.nombre = nombre_antiguo
                flash(f"El nombre '{nuevo_nombre}' ya está en uso. Por favor, elige otro.", "danger")
        
        # --- Lógica para subir avatar ---
        if "avatar" in request.files:
            file = request.files["avatar"]
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"user_{estudiante.id}_{file.filename}")
                path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                try:
                    file.save(path)
                    estudiante.avatar_personal = filename
                    db.session.commit() # Guardamos el cambio del avatar
                    flash("Avatar actualizado correctamente.", "success")
                    procesar_accion_gamificada(estudiante.id, 'cambiar_avatar') # Usando procesar_accion_gamificada
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

    estudiante.puntos = 0 # Reiniciar puntos a 0 o al valor inicial que desees
    estudiante.xp = 0
    estudiante.nivel = 1
    estudiante.avatar_personal = 'avatar-1.png'
    estudiante.marco_personal = 'marco-1.png'
    estudiante.fondo_personal = None
    
    # Borrar inventario, progreso de misiones y logros del estudiante
    Inventario.query.filter_by(estudiante_id=estudiante.id).delete()
    ProgresoMision.query.filter_by(estudiante_id=estudiante.id).delete()
    estudiante.logros = [] # Borra las relaciones en la tabla intermedia estudiante_logros
    # RESTAURADO: Borrar actividades completadas
    EstudianteActividadCompletada.query.filter_by(estudiante_id=estudiante.id).delete()

    db.session.commit()
    flash("¡Tu progreso ha sido reiniciado! ¡Empieza de nuevo!", "info")
    return redirect(url_for("index"))

# --- Rutas de Juegos ---
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

# Estas rutas POST para tictactoe_ganar/perder son redundantes con /juego/resultado
# Si tu frontend ya usa /juego/resultado, puedes eliminar estas:
@app.route("/juego/tictactoe/ganar", methods=["POST"])
@login_required
def tictactoe_ganar():
    # Esta ruta debería ser manejada por /juego/resultado para consistencia
    # Si la dejas, asegúrate de que use la misma lógica de XP/Puntos/Misiones/Nivel/Logros
    flash("Usa la ruta /juego/resultado para enviar los resultados del juego.", "warning")
    return jsonify({"status": "deprecated", "message": "Por favor, usa /juego/resultado"})

@app.route("/juego/tictactoe/perder", methods=["POST"])
@login_required
def tictactoe_perder():
    # Esta ruta debería ser manejada por /juego/resultado para consistencia
    flash("Usa la ruta /juego/resultado para enviar los resultados del juego.", "warning")
    return jsonify({"status": "deprecated", "message": "Por favor, usa /juego/resultado"})

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
    resultado = data.get('resultado') # 'ganado', 'perdido', 'jugado', 'empatado'
    dificultad = data.get('dificultad', 'normal') # Obtener la dificultad

    if not all([juego, resultado, estudiante]):
        return jsonify({"status": "error", "message": "Datos incompletos para procesar el resultado del juego."}), 400

    # Las llamadas a procesar_accion_gamificada ahora manejan la suma de puntos y XP de misiones
    if juego == 'memoria':
        procesar_accion_gamificada(estudiante.id, 'jugar_memoria') 
        if resultado == 'ganado':
            procesar_accion_gamificada(estudiante.id, 'ganar_memoria')
        # Puedes añadir lógica para 'perdido' o 'empatado' en memoria si es necesario

    elif juego == 'tictactoe':
        procesar_accion_gamificada(estudiante.id, 'jugar_tictactoe')
        config = DIFICULTAD_TICTACTOE.get(dificultad, DIFICULTAD_TICTACTOE['normal'])
        if resultado == 'ganado':
            procesar_accion_gamificada(estudiante.id, 'ganar_tictactoe')
        elif resultado == 'perdido':
            # La penalización de puntos directa si no hay una misión específica de 'perder'
            estudiante.puntos = max(0, estudiante.puntos - config['penalizacion']) 
            # Si hubiera una misión de perder, se llamaría: procesar_accion_gamificada(estudiante.id, 'perder_tictactoe')
        elif resultado == 'empatado':
            # Si hubiera una misión de empatar, se llamaría: procesar_accion_gamificada(estudiante.id, 'empatar_tictactoe')
            pass 
    
    # Las llamadas a verificar_y_actualizar_nivel y verificar_y_asignar_logros
    # ya se hacen dentro de procesar_accion_gamificada cuando se completa una misión.
    # Si sumas puntos/XP directamente aquí (como en la penalización de tictactoe),
    # DEBES llamar a estas funciones de nuevo.
    # Por ejemplo, si penalizas puntos, el nivel podría bajar (aunque no es común) o no afectar la XP.
    # Es mejor que la lógica de nivel/logros se ejecute después de CUALQUIER cambio de XP/Puntos.
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
    """
    Función que inyecta datos del usuario en todas las plantillas,
    útil para la barra lateral o el header.
    """
    if 'estudiante_id' not in session:
        return {} 
    
    estudiante = db.session.get(Estudiante, session['estudiante_id'])
    if not estudiante:
        # Si el estudiante no se encuentra (ej. eliminado de la DB), limpiar la sesión
        session.pop('estudiante_id', None)
        return {}
    
    # Contar cuántas misiones NO están completadas
    misiones_activas_count = sum(1 for p in estudiante.progreso_misiones if not p.completada)
        
    return dict(
        name=estudiante.nombre,
        avatar=estudiante.avatar_personal,
        marco=estudiante.marco_personal,
        misiones_sidebar=[p for p in estudiante.progreso_misiones if not p.completada], # Solo misiones activas para la sidebar
        misiones_activas_count=misiones_activas_count
    )

# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        password = request.form.get('password')

        # Validaciones básicas
        if not nombre or not email or not password:
            flash('Por favor, completa todos los campos.', 'danger')
            return redirect(url_for('registro'))
        if len(nombre) < 3 or len(nombre) > 30:
            flash('El nombre de usuario debe tener entre 3 y 30 caracteres.', 'danger')
            return redirect(url_for('registro'))
        if len(password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return redirect(url_for('registro'))

        # Verifica si el email o nombre ya existen
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
@login_required # Solo usuarios logueados pueden cerrar sesión
def logout():
    session.pop('estudiante_id', None)
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('login'))

# --- PUNTO DE INICIO DE LA APLICACIÓN ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all() # ¡IMPORTANTE! Crea todas las tablas si no existen

        # --- Opcional: Poblar la DB con datos iniciales si está vacía ---
        if not Mision.query.first():
            print("Poblando base de datos con misiones iniciales...")
            misiones_iniciales = [
                # Misiones con action_trigger
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
                Objeto(nombre="Avatar de Panda", tipo="avatar", descripcion="Un adorable avatar de panda.", imagen_url="avatar-2.png", precio=50),
                Objeto(nombre="Avatar de Cohete", tipo="avatar", descripcion="Un avatar que te llevará a las estrellas.", imagen_url="avatar-3.png", precio=75),
                Objeto(nombre="Marco Estelar", tipo="marco", descripcion="Un marco brillante para tu perfil.", imagen_url="marco-2.png", precio=100),
                Objeto(nombre="Marco de Bosque", tipo="marco", descripcion="Un marco que te conecta con la naturaleza.", imagen_url="marco-3.png", precio=80),
                # Puedes añadir más objetos, fondos, etc.
            ]
            db.session.add_all(objetos_iniciales)

            logros_iniciales = [
                Logro(nombre="Novato Gamificado", descripcion="Alcanza el nivel 2.", imagen_url="logro-novato.png", nivel_requerido=2),
                Logro(nombre="Aprendiz Experto", descripcion="Alcanza el nivel 5.", imagen_url="logro-experto.png", nivel_requerido=5),
                Logro(nombre="Maestro de Puntos", descripcion="Consigue 500 puntos.", imagen_url="logro-puntos.png", nivel_requerido=1), # Se puede ajustar la condición para puntos si la agregas como tipo de logro
            ]
            db.session.add_all(logros_iniciales)

            # NUEVAS ACTIVIDADES INICIALES
            actividades_iniciales = [
                Actividad(nombre="Lectura de Artículo", descripcion="Lee un artículo científico sobre IA.", puntos_recompensa=10),
                Actividad(nombre="Participación en Foro", descripcion="Publica una pregunta o respuesta en el foro del curso.", puntos_recompensa=10),
                Actividad(nombre="Asistencia a Webinar", descripcion="Asiste a un webinar de la UBE.", puntos_recompensa=10),
                Actividad(nombre="Entrega de Tarea Extra", descripcion="Entrega una tarea opcional para puntos extra.", puntos_recompensa=10),
            ]
            db.session.add_all(actividades_iniciales)

            db.session.commit()
            print("Datos iniciales de misiones, objetos, logros y actividades añadidos.")
        else:
            print("La base de datos ya contiene misiones, no se añadieron datos iniciales.")

    app.run(debug=True) # Establece debug=False en producción
