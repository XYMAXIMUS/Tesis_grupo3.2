-- Tabla de estudiantes
CREATE TABLE IF NOT EXISTS estudiantes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    puntos INT DEFAULT 1000,
    xp INT DEFAULT 0,
    nivel INT DEFAULT 1,
    avatar_personal VARCHAR(255),
    marco VARCHAR(255),
    fondo VARCHAR(255),
    UNIQUE KEY nombre_unique (nombre)
);

-- Tabla de objetos
CREATE TABLE IF NOT EXISTS objetos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    precio INT NOT NULL,
    imagen VARCHAR(255) NOT NULL,
    tipo ENUM('avatar', 'marco', 'fondo') NOT NULL,
    UNIQUE KEY nombre_unique (nombre)
);

-- Tabla de inventario (relación entre estudiantes y objetos)
CREATE TABLE IF NOT EXISTS inventario (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    objeto_id INT NOT NULL,
    fecha_obtenido DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
    FOREIGN KEY (objeto_id) REFERENCES objetos(id),
    UNIQUE KEY unique_inventario (estudiante_id, objeto_id)
);

-- Tabla de logros especiales
CREATE TABLE IF NOT EXISTS logros_especiales (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    imagen VARCHAR(255) NOT NULL,
    requisito TEXT,
    puntos_bonus INT DEFAULT 0,
    xp_bonus INT DEFAULT 0,
    UNIQUE KEY nombre_unique (nombre)
);

-- Tabla de logros equipados
CREATE TABLE IF NOT EXISTS logros_equipados (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    logro_id INT NOT NULL,
    fecha_equipado DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
    FOREIGN KEY (logro_id) REFERENCES logros_especiales(id),
    UNIQUE KEY unique_logro_equipado (estudiante_id, logro_id)
);

-- Tabla de misiones
CREATE TABLE IF NOT EXISTS misiones_config (
    id VARCHAR(50) PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    puntos_recompensa INT NOT NULL,
    xp_recompensa INT NOT NULL,
    requisito TEXT
);

-- Tabla de progreso de misiones
CREATE TABLE IF NOT EXISTS progreso_misiones (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    mision_id VARCHAR(50) NOT NULL,
    progreso INT DEFAULT 0,
    fecha_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
    FOREIGN KEY (mision_id) REFERENCES misiones_config(id),
    UNIQUE KEY unique_progreso (estudiante_id, mision_id)
);

-- Tabla de medallas
CREATE TABLE IF NOT EXISTS medallas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    imagen VARCHAR(255) NOT NULL,
    requisito TEXT,
    puntos_bonus INT DEFAULT 0,
    xp_bonus INT DEFAULT 0,
    UNIQUE KEY nombre_unique (nombre)
);

-- Tabla de medallas obtenidas
CREATE TABLE IF NOT EXISTS medallas_obtenidas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    medalla_id INT NOT NULL,
    fecha_obtenida DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
    FOREIGN KEY (medalla_id) REFERENCES medallas(id),
    UNIQUE KEY unique_medalla_obtenida (estudiante_id, medalla_id)
);

-- Tabla de juegos
CREATE TABLE IF NOT EXISTS juegos (
    id INT PRIMARY KEY AUTO_INCREMENT,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    puntos_base INT NOT NULL,
    xp_base INT NOT NULL,
    UNIQUE KEY nombre_unique (nombre)
);

-- Tabla de partidas
CREATE TABLE IF NOT EXISTS partidas (
    id INT PRIMARY KEY AUTO_INCREMENT,
    estudiante_id INT NOT NULL,
    juego_id INT NOT NULL,
    fecha_jugada DATETIME DEFAULT CURRENT_TIMESTAMP,
    resultado ENUM('ganado', 'perdido') NOT NULL,
    puntos_obtenidos INT NOT NULL,
    xp_obtenido INT NOT NULL,
    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id),
    FOREIGN KEY (juego_id) REFERENCES juegos(id)
);
