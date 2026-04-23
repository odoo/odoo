# Part of Odoo. See LICENSE file for full copyright and licensing details.
from stdnum.ar import cuit as ar_cuit, dni as ar_dni

from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

AR_CUIT_AFIP_CODE = '80'
AR_FOREIGN_ID_AFIP_CODE = '91'  # CI extranjera
AR_SIGD_AFIP_CODE = '99'  # Sin identificar / venta global diaria

# AFIP identification codes (catálogo A4)
AR_AFIP_CODES = {
    'AR_AN': '93',
    'AR_CDI': '87',
    'AR_CDM': '30',
    'AR_CIBAR': '95',
    'AR_CPF': '0',
    'AR_CUIL': '86',
    'AR_DNI': '96',
    'AR_ET': '92',
    'AR_LC': '90',
    'AR_LE': '89',
    'AR_SIGD': AR_SIGD_AFIP_CODE,
    'AR_UPAPP': '88',
    'PASSPORT': '94',
}

AR_STATE_TO_CI_AFIP_CODE = {
    'B': '1',   # Buenos Aires
    'K': '2',   # Catamarca
    'X': '3',   # Córdoba
    'W': '4',   # Corrientes
    'E': '5',   # Entre Ríos
    'Y': '6',   # Jujuy
    'M': '7',   # Mendoza
    'F': '8',   # La Rioja
    'A': '9',   # Salta
    'J': '10',  # San Juan
    'D': '11',  # San Luis
    'S': '12',  # Santa Fe
    'G': '13',  # Santiago del Estero
    'T': '14',  # Tucumán
    'H': '16',  # Chaco
    'U': '17',  # Chubut
    'P': '18',  # Formosa
    'N': '19',  # Misiones
    'Q': '20',  # Neuquén
    'L': '21',  # La Pampa
    'R': '22',  # Río Negro
    'Z': '23',  # Santa Cruz
    'V': '24',  # Tierra del Fuego
}

AR_ADDITIONAL_IDENTIFIERS_METADATA = {
    'AR_AN': {
        'label': _lt('AN'),
        'help': _lt('Birth certificate / Acta de nacimiento.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CDI': {
        'label': _lt('CDI'),
        'help': _lt('Identification Code.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CDM': {
        'label': _lt('CdM'),
        'help': _lt('Migration Certificate / Certificado de migración.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CI': {
        'label': _lt('CI'),
        'help': _lt("Provincial ID card (Cédula de Identidad); the AFIP document type is derived from the partner's province."),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CIBAR': {
        'label': _lt('CIBAR'),
        'help': _lt('CI Bs. As. RNP.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CPF': {
        'label': _lt('CPF'),
        'help': _lt('CI Federal Police.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_CUIL': {
        'sequence': 30,
        'label': _lt('CUIL'),
        'help': _lt('Unique Labor Identification Code (Código Único de Identificación Laboral).'),
        'category': 'CN',
        'validation_function': ar_cuit.validate,
        'countries': ['AR'],
    },
    'AR_DNI': {
        'sequence': 20,
        'label': _lt('DNI'),
        'help': _lt('National Identity Card (Documento Nacional de Identidad).'),
        'placeholder': '34586675',
        'category': 'CN',
        'validation_function': ar_dni.validate,
        'countries': ['AR'],
    },
    'AR_ET': {
        'label': _lt('ET'),
        'help': _lt('Pending (en trámite).'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_LC': {
        'label': _lt('LC'),
        'help': _lt('Libreta cívica.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_LE': {
        'label': _lt('LE'),
        'help': _lt('Libreta de enrolamiento.'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_SIGD': {
        'sequence': 110,
        'label': _lt('SIGD'),
        'help': _lt('Unidentified / global daily sales (Sin identificar / venta global diaria).'),
        'category': 'CN',
        'countries': ['AR'],
    },
    'AR_UPAPP': {
        'label': _lt('UpApP'),
        'help': _lt('Used by Anses for Padrón.'),
        'category': 'CN',
        'countries': ['AR'],
    },
}
