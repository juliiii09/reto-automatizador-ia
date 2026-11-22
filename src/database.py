import csv
import json
import sqlite3
from pathlib import Path

RUTA_DB = "rrhh.db"
CARPETA_SALIDA = Path("outputs")


def crear_tablas():
    """Crea la base de datos SQLite y las tablas empleados y solicitudes."""
    with sqlite3.connect(RUTA_DB) as conn:
        cursor = conn.cursor()

        # Tabla empleados
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS empleados (
                id_empleado TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL,
                area TEXT NOT NULL,
                cargo TEXT NOT NULL,
                fecha_ingreso TEXT NOT NULL,
                dias_vacaciones_disponibles INTEGER NOT NULL CHECK (dias_vacaciones_disponibles >= 0),
                documento TEXT NOT NULL
            )
        """)

        # Tabla solicitudes (sin FOREIGN KEY estricta para conservar casos como E009)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS solicitudes (
                id_solicitud TEXT PRIMARY KEY,
                id_empleado TEXT NOT NULL,
                fecha_recepcion TEXT NOT NULL,
                canal TEXT NOT NULL,
                texto TEXT NOT NULL,
                etiqueta_esperada TEXT NOT NULL
            )
        """)

        conn.commit()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print("Tablas creadas:", cursor.fetchall())


def limpiar_empleados():
    """Lee empleados.csv, limpia las inconsistencias y devuelve la lista lista para SQLite."""
    empleados_limpios = []
    ids_vistos = set()

    with open("empleados.csv", mode="r", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            # 1. Duplicados
            id_emp = fila["id_empleado"].strip()
            if id_emp in ids_vistos:
                print("Duplicado descartado:", id_emp)
                continue
            ids_vistos.add(id_emp)

            # 2. Correo
            correo = fila["correo"].strip().lower()
            if fila["correo"] != correo:
                print("Correo normalizado en:", id_emp)

            # 3. Área vacía
            area = fila["area"].strip()
            if area == "":
                area = "Sin área"
                print("Área vacía reemplazada en:", id_emp)

            # 4. Días de vacaciones (texto -> número entero)
            dias = int(fila["dias_vacaciones_disponibles"].strip())

            # 5. Guardar el empleado limpio en la lista
            empleados_limpios.append({
                "id_empleado": id_emp,
                "nombre": fila["nombre"].strip(),
                "correo": correo,
                "area": area,
                "cargo": fila["cargo"].strip(),
                "fecha_ingreso": fila["fecha_ingreso"].strip(),
                "dias_vacaciones_disponibles": dias,
                "documento": fila["documento"].strip(),
            })

    return empleados_limpios


def limpiar_solicitudes():
    """Lee solicitudes.json y limpia espacios/mayúsculas en cada registro."""
    solicitudes_limpias = []
    ids_vistos = set()

    with open("solicitudes.json", mode="r", encoding="utf-8") as archivo:
        datos = json.load(archivo)
        for item in datos:
            id_sol = item["id_solicitud"].strip()
            if id_sol in ids_vistos:
                print("Solicitud duplicada descartada:", id_sol)
                continue
            ids_vistos.add(id_sol)

            solicitudes_limpias.append({
                "id_solicitud": id_sol,
                "id_empleado": item["id_empleado"].strip(),
                "fecha_recepcion": item["fecha_recepcion"].strip(),
                "canal": item["canal"].strip().lower(),
                "texto": item["texto"].strip(),
                "etiqueta_esperada": item["etiqueta_esperada"].strip().upper(),
            })

    return solicitudes_limpias


def cargar_datos(empleados, solicitudes):
    """Inserta empleados y solicitudes limpias en SQLite de forma idempotente."""
    with sqlite3.connect(RUTA_DB) as conn:
        cursor = conn.cursor()

        # Limpiar antes para poder re-ejecutar el script sin errores de llave duplicada
        cursor.execute("DELETE FROM solicitudes")
        cursor.execute("DELETE FROM empleados")

        cursor.executemany("""
            INSERT INTO empleados (
                id_empleado, nombre, correo, area, cargo,
                fecha_ingreso, dias_vacaciones_disponibles, documento
            ) VALUES (
                :id_empleado, :nombre, :correo, :area, :cargo,
                :fecha_ingreso, :dias_vacaciones_disponibles, :documento
            )
        """, empleados)

        cursor.executemany("""
            INSERT INTO solicitudes (
                id_solicitud, id_empleado, fecha_recepcion,
                canal, texto, etiqueta_esperada
            ) VALUES (
                :id_solicitud, :id_empleado, :fecha_recepcion,
                :canal, :texto, :etiqueta_esperada
            )
        """, solicitudes)

        conn.commit()

        total_emp = cursor.execute("SELECT COUNT(*) FROM empleados").fetchone()[0]
        total_sol = cursor.execute("SELECT COUNT(*) FROM solicitudes").fetchone()[0]
        print(f"Cargados en SQLite -> empleados: {total_emp}, solicitudes: {total_sol}")


def ejecutar_consultas():
    """Ejecuta las 3 consultas SQL de Misión 1 y guarda cada resultado en outputs/."""
    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)

    consultas = {
        "consulta_a_categoria_area.csv": """
            SELECT
                s.etiqueta_esperada AS categoria,
                COALESCE(e.area, 'Sin nómina') AS area,
                COUNT(*) AS total_solicitudes
            FROM solicitudes s
            LEFT JOIN empleados e ON s.id_empleado = e.id_empleado
            GROUP BY s.etiqueta_esperada, COALESCE(e.area, 'Sin nómina')
            ORDER BY categoria, area
        """,
        "consulta_b_empleados_inexistentes.csv": """
            SELECT
                s.id_solicitud,
                s.id_empleado,
                s.fecha_recepcion,
                s.canal,
                s.texto
            FROM solicitudes s
            LEFT JOIN empleados e ON s.id_empleado = e.id_empleado
            WHERE e.id_empleado IS NULL
            ORDER BY s.id_solicitud
        """,
        "consulta_c_pocas_vacaciones.csv": """
            SELECT
                id_empleado,
                nombre,
                area,
                dias_vacaciones_disponibles
            FROM empleados
            WHERE dias_vacaciones_disponibles < 5
            ORDER BY dias_vacaciones_disponibles ASC, id_empleado ASC
        """,
    }

    with sqlite3.connect(RUTA_DB) as conn:
        cursor = conn.cursor()
        for nombre_archivo, sql in consultas.items():
            cursor.execute(sql)
            columnas = [col[0] for col in cursor.description]
            filas = cursor.fetchall()

            ruta_csv = CARPETA_SALIDA / nombre_archivo
            with ruta_csv.open(mode="w", encoding="utf-8", newline="") as archivo:
                escritor = csv.writer(archivo)
                escritor.writerow(columnas)
                escritor.writerows(filas)

            print(f"\n--- {nombre_archivo} ({len(filas)} filas) ---")
            for fila in filas:
                print(" ", fila)


if __name__ == "__main__":
    crear_tablas()
    empleados = limpiar_empleados()
    solicitudes = limpiar_solicitudes()
    cargar_datos(empleados, solicitudes)
    ejecutar_consultas()
