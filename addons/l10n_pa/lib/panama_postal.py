# Panama postal code codec, vendored from panama-postal
# https://github.com/kass507/panama-postal (fork: alvarosamudio/panama-postal)
# Copyright (c) 2026 kass507
# Licensed under the MIT License. See l10n_pa/LICENSE-panama-postal.
"""
Codec de Códigos Postales de Panamá.

Decodifica códigos como ACC99-PJ42W a coordenadas (lat, lng) y viceversa.
Implementación basada en ingeniería inversa del bundle JS oficial de
codigospostalespanama.gob.pa (mayo 2026).
"""


from dataclasses import dataclass

ALPHABET = "23456789ABCDEFGHJKLMNPQRSTVWXZ" # Por lo que pude evr no usar I/O/U/Y para evitar confusiones visuales.
ALPHA_INDEX = {ch: i for i, ch in enumerate(ALPHABET)}

ORIGIN_LAT = 10.0
ORIGIN_LNG = -83.5

STEP_MACRO = 0.1425
STEP_MICRO = 0.1425 / 24
STEP_NANO = 0.0059375 / 25
STEP_PICO = 2375e-7 / 8

# Dimensiones de subdivisión de cada celda
MACRO_COLS = 40
MICRO_COLS, MICRO_ROWS = 24, 24
NANO_COLS, NANO_ROWS = 25, 25
PICO_COLS, PICO_ROWS = 8, 8


@dataclass
class DecodedPostal:
    lat: float
    lng: float
    precision_meters: float  
    level: str 
    estafeta_prefix: str | None


def _encode_pair(value: int) -> str:
    """Codifica un entero 0..899 como 2 caracteres base-30."""
    return ALPHABET[value // 30] + ALPHABET[value % 30]


def _decode_pair(pair: str) -> int:
    """
    Decodifica 2 caracteres base-30 a entero.
    """
    return ALPHA_INDEX[pair[0]] * 30 + ALPHA_INDEX[pair[1]]


def _normalize(code: str) -> tuple[str, str | None]:
    """
    Quita guiones/espacios, pasa a mayúsculas y separa el prefijo de estafeta.

    Devuelve (cuerpo, prefijo_estafeta) o ("", None) si la entrada es inválida.

    Reglas estrictas:
    - Solo se permiten letras/dígitos del alfabeto base-30, más guiones y espacios.
    - Cualquier otro caracter (puntuación, letras como I/O/U/Y, etc.) → inválido.
    - Longitud final del cuerpo debe ser 2, 4, 6, 8 o 10.
    """
    if not isinstance(code, str):
        return "", None

    clean = code.replace("-", "").replace(" ", "").upper()
    if not clean or len(clean) > 10:
        return "", None

    if any(ch not in ALPHA_INDEX for ch in clean):
        return "", None

    if len(clean) == 10:
        return clean[2:], clean[:2]
    if len(clean) % 2 == 1:
        return "", None
    return clean, None


def decode(code: str) -> DecodedPostal | None:
    """
    Decodifica un código postal panameño a (lat, lng) del centro de la celda.

    Acepta formatos: "M9C9A-G4434", "M9C9AG4434", "ACC99-PJ42W", "ACC99PJ42W", etc.
    Devuelve None si el código es inválido.
    """
    body, prefix = _normalize(code)
    if not body:
        return None

    lat = ORIGIN_LAT
    lng = ORIGIN_LNG
    level = "MACRO"
    precision = STEP_MACRO * 111_000  # grados a metros aprox

    # Nivel MACRO (caracteres 0-1)
    if len(body) >= 2:
        macro = _decode_pair(body[0:2])
        macro_row = macro // MACRO_COLS
        macro_col = macro % MACRO_COLS
        lat = ORIGIN_LAT
        lng = ORIGIN_LNG
        lat -= macro_row * STEP_MACRO - STEP_MACRO / 2
        lng += macro_col * STEP_MACRO + STEP_MACRO / 2
        level, precision = "MACRO", STEP_MACRO * 111_000

    # Nivel MICRO (caracteres 2-3)
    if len(body) >= 4:
        macro = _decode_pair(body[0:2])
        macro_row, macro_col = macro // MACRO_COLS, macro % MACRO_COLS
        micro = _decode_pair(body[2:4])
        micro_row = micro // MICRO_COLS
        micro_col = micro % MICRO_COLS
        # Esquina NO de la celda MACRO
        macro_lat = ORIGIN_LAT - macro_row * STEP_MACRO
        macro_lng = ORIGIN_LNG + macro_col * STEP_MACRO
        lat = macro_lat - micro_row * STEP_MICRO - STEP_MICRO / 2
        lng = macro_lng + micro_col * STEP_MICRO + STEP_MICRO / 2
        level, precision = "MICRO", STEP_MICRO * 111_000

    # Nivel NANO (caracteres 4-5)
    if len(body) >= 6:
        macro = _decode_pair(body[0:2])
        macro_row, macro_col = macro // MACRO_COLS, macro % MACRO_COLS
        micro = _decode_pair(body[2:4])
        micro_row, micro_col = micro // MICRO_COLS, micro % MICRO_COLS
        nano = _decode_pair(body[4:6])
        nano_row = nano // NANO_COLS
        nano_col = nano % NANO_COLS
        macro_lat = ORIGIN_LAT - macro_row * STEP_MACRO - micro_row * STEP_MICRO
        macro_lng = ORIGIN_LNG + macro_col * STEP_MACRO + micro_col * STEP_MICRO
        lat = macro_lat - nano_row * STEP_NANO - STEP_NANO / 2
        lng = macro_lng + nano_col * STEP_NANO + STEP_NANO / 2
        level, precision = "NANO", STEP_NANO * 111_000

    # Nivel PICO (caracteres 6-7) — precisión final ~3 m
    if len(body) >= 8:
        macro = _decode_pair(body[0:2])
        macro_row, macro_col = macro // MACRO_COLS, macro % MACRO_COLS
        micro = _decode_pair(body[2:4])
        micro_row, micro_col = micro // MICRO_COLS, micro % MICRO_COLS
        nano = _decode_pair(body[4:6])
        nano_row, nano_col = nano // NANO_COLS, nano % NANO_COLS
        pico = _decode_pair(body[6:8])
        pico_row = pico // PICO_COLS
        pico_col = pico % PICO_COLS
        macro_lat = (ORIGIN_LAT
                     - macro_row * STEP_MACRO
                     - micro_row * STEP_MICRO
                     - nano_row * STEP_NANO)
        macro_lng = (ORIGIN_LNG
                     + macro_col * STEP_MACRO
                     + micro_col * STEP_MICRO
                     + nano_col * STEP_NANO)
        lat = macro_lat - pico_row * STEP_PICO - STEP_PICO / 2
        lng = macro_lng + pico_col * STEP_PICO + STEP_PICO / 2
        level, precision = "PICO", STEP_PICO * 111_000

    return DecodedPostal(
        lat=lat,
        lng=lng,
        precision_meters=round(precision, 2),
        level=level,
        estafeta_prefix=prefix,
    )


def encode(lat: float, lng: float, level: str = "PICO") -> str:
    """
    Codifica (lat, lng) a la PARTE GEOGRÁFICA del código postal (sin prefijo de estafeta).

    El prefijo (ej. "AC") requiere el archivo estafeta.geojson para hacer point-in-polygon.
    Esta función devuelve los 2/4/6/8 caracteres del cuerpo según el nivel pedido.

    Para el código completo con prefijo, usar además la tabla de estafetas.
    """
    if level not in ("MACRO", "MICRO", "NANO", "PICO"):
        raise ValueError(f"Nivel inválido: {level}")

    dlng = lng - ORIGIN_LNG
    dlat = ORIGIN_LAT - lat

    macro_col = int(dlng // STEP_MACRO)
    macro_row = int(dlat // STEP_MACRO)
    macro_code = _encode_pair(macro_row * MACRO_COLS + macro_col)
    if level == "MACRO":
        return macro_code

    rem_lng = dlng % STEP_MACRO
    rem_lat = dlat % STEP_MACRO
    micro_col = int(rem_lng // STEP_MICRO)
    micro_row = int(rem_lat // STEP_MICRO)
    micro_code = _encode_pair(micro_row * MICRO_COLS + micro_col)
    if level == "MICRO":
        return f"{macro_code}{micro_code}"  # 4 chars

    rem_lng = rem_lng % STEP_MICRO
    rem_lat = rem_lat % STEP_MICRO
    nano_col = int(rem_lng // STEP_NANO)
    nano_row = int(rem_lat // STEP_NANO)
    nano_code = _encode_pair(nano_row * NANO_COLS + nano_col)
    if level == "NANO":
        # El sitio formatea con un guion en el medio del string total.
        # 6 chars de cuerpo → "XXY-YZZ"
        body = f"{macro_code}{micro_code}{nano_code}"
        return f"{body[:3]}-{body[3:]}"

    rem_lng = rem_lng % STEP_NANO
    rem_lat = rem_lat % STEP_NANO
    pico_col = int(rem_lng // STEP_PICO)
    pico_row = int(rem_lat // STEP_PICO)
    pico_code = _encode_pair(pico_row * PICO_COLS + pico_col)
    # 8 chars de cuerpo → "XXY-YZZWW" (guion tras el carácter 3,
    # que es como queda al partir por la mitad un string de 10 chars
    # cuando se le antepone un prefijo de 2 caracteres)
    body = f"{macro_code}{micro_code}{nano_code}{pico_code}"
    return f"{body[:3]}-{body[3:]}"


def is_in_panama(lat: float, lng: float, strict: bool = False) -> bool:
    """
    Verifica si las coordenadas caen en el área de Panamá.

    Por defecto usa el mismo bbox laxo que el sitio oficial:
        lat ∈ [6, 11], lng ∈ [-86, -74]
    Este bbox cubre Panamá entera con mucho margen (incluye partes
    de Costa Rica, Colombia y mar Caribe/Pacífico).

    Con strict=True usa un bbox ajustado al territorio real:
        lat ∈ [7.15, 9.70], lng ∈ [-83.10, -77.10]
    """
    if strict:
        return 7.15 <= lat <= 9.70 and -83.10 <= lng <= -77.10
    return 6.0 <= lat <= 11.0 and -86.0 <= lng <= -74.0


def validate(code: str, strict: bool = False) -> bool:
    """
    Valida un código postal: que tenga formato correcto Y caiga en Panamá.

    Por defecto usa el mismo bbox laxo que el sitio oficial.
    Con strict=True aplica el bbox ajustado al territorio.
    """
    decoded = decode(code)
    if decoded is None:
        return False
    return is_in_panama(decoded.lat, decoded.lng, strict=strict)

