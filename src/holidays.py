import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests

RUTA_RESPALDO = Path("outputs/festivos_2026_CO.json")

def obtener_festivos(anio=2026, pais="CO", intentos=3, timeout=10):
    url = f"https://date.nager.at/api/v3/PublicHolidays/{anio}/{pais}"

# intentar consultar a la API
    for intento in range(1, intentos + 1):
        try:
            respuesta = requests.get(url, timeout=timeout)
            respuesta.raise_for_status()
            datos = respuesta.json()

# guardar el respaldo local si la API RESPONDE BIEN
            RUTA_RESPALDO.parent.mkdir(parents=True, exist_ok=True)
            with RUTA_RESPALDO.open(mode="w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2) 
            return {item["date"] for item in datos}
        except requests.RequestException as error:
            print(f"Intento {intento}/{intentos} falló: {error}")
            if intento < intentos:
                time.sleep(1)


 # 2. Plan B: si fallaron todos los intentos, usar respaldo local
    if RUTA_RESPALDO.exists():
        print("Usando respaldo local de festivos:", RUTA_RESPALDO)
        with RUTA_RESPALDO.open(mode="r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
        return {item["date"] for item in datos}
    raise RuntimeError("No se pudieron obtener los festivos ni de la API ni del respaldo local.")



# calcular dias habiles
def calcular_dias_habiles(fecha_inicio, fecha_fin, festivos):
    inicio = date.fromisoformat(fecha_inicio)
    fin = date.fromisoformat(fecha_fin)

    if fin < inicio:
        raise ValueError("La fecha_fin no puede ser anterior a fecha_inicio.")

    dias_habiles = 0
    dia_actual = inicio

    while dia_actual <= fin:
        es_entre_semana = dia_actual.weekday() < 5  # 0=lunes ... 4=viernes
        es_festivo = dia_actual.isoformat() in festivos

        if es_entre_semana and not es_festivo:
            dias_habiles += 1

        dia_actual += timedelta(days=1)

    return dias_habiles




if __name__ == "__main__":
    festivos = obtener_festivos()
    print("Total festivos 2026:", len(festivos))
    print("¿Es festivo 2026-12-08?", "2026-12-08" in festivos)
    print("¿Es festivo 2026-12-25?", "2026-12-25" in festivos)

    print("S01 (esperado 5):", calcular_dias_habiles("2026-12-14", "2026-12-18", festivos))
    print("S05 (esperado 4):", calcular_dias_habiles("2026-12-07", "2026-12-11", festivos))
    print("S06 (esperado 8):", calcular_dias_habiles("2026-12-21", "2026-12-31", festivos))
                    

