# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Map AR-specific additional identifiers to the AFIP catalog code reported on
# EDI/legal documents. CUIT (80) lives on `vat` (country=AR) and is resolved
# separately.
AR_IDENTIFIER_TO_AFIP_CODE = {
    'AR_CUIL': '86',
    'AR_DNI': '96',
    'PASSPORT': '94',
    'AR_SIGD': '99',
    'AR_CDI': '87',
    'AR_LE': '89',
    'AR_LC': '90',
    'AR_ET': '92',
    'AR_AN': '93',
    'AR_CIBAR': '95',
    'AR_CDM': '30',
    'AR_UPAPP': '88',
    # CI Federal Police and CI Bs. As. RNP (AR_CIBAR, above) are not 1:1 with a
    # province, so they keep their own explicit codes instead of being derived
    # from the address.
    'AR_CPF': '0',
}

# The generic provincial ID (`AR_CI`) does not carry its own AFIP code: the
# document type is derived from the partner's province. Map each Argentine
# `res.country.state` code (base.state_ar_*) to the AFIP catalog code.
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
