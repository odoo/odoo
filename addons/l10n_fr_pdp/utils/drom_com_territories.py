"""
DROM-COM Territory Management for French E-Invoicing/E-Reporting Reform

This module handles the specific rules for Overseas Departments and Collectivities
(Départements et Régions d'Outre-Mer et Collectivités d'Outre-Mer) according to
the French tax reform specifications.
"""

# -------------------------------------------------------------------------
# Territory Definitions
# -------------------------------------------------------------------------

# DROM - Départements et Régions d'Outre-Mer
# These territories have specific VAT regimes

# Group A: Similar to Metropolitan France for VAT
# Subject to E-invoicing with Metropolitan France and between them
DROM_E_INVOICING = {
    'GP',  # Guadeloupe
    'MQ',  # Martinique
    'RE',  # La Réunion
}

# Group B: Specific VAT regimes (export/import logic)
# Generally subject to E-reporting rather than e-invoicing
DROM_E_REPORTING = {
    'GF',  # Guyane (French Guiana)
    'YT',  # Mayotte
}

# COM - Collectivités d'Outre-Mer
# Treated as non-domestic territories, subject to E-reporting
COM_TERRITORIES = {
    'BL',  # Saint-Barthélemy
    'MF',  # Saint-Martin
    'PM',  # Saint-Pierre-et-Miquelon
    'PF',  # Polynésie Française (French Polynesia)
    'WF',  # Wallis-et-Futuna
    'TF',  # TAAF (Terres Australes et Antarctiques Françaises)
    'NC',  # Nouvelle-Calédonie (New Caledonia)
}

# All French overseas territories
ALL_DROM_COM = DROM_E_INVOICING | DROM_E_REPORTING | COM_TERRITORIES

# Metropolitan France
FRANCE_METRO = {'FR'}

# Complete list of French territories (metro + overseas)
ALL_FRANCE_TERRITORIES = FRANCE_METRO | ALL_DROM_COM

# -------------------------------------------------------------------------
# Country Code Mapping for PPF XML Flows
# -------------------------------------------------------------------------

# According to technical specifications, these ISO country codes must be
# mapped to 'FR' in XML flows (Flux 1 & Flux 10) transmitted to the PPF
COUNTRY_CODE_MAPPED_TO_FR = {
    'GP',  # Guadeloupe
    'MQ',  # Martinique
    'GF',  # Guyane
    'RE',  # La Réunion
    'YT',  # Mayotte
    'BL',  # Saint-Barthélemy
    'MF',  # Saint-Martin
    'PM',  # Saint-Pierre-et-Miquelon
    'WF',  # Wallis-et-Futuna
    'TF',  # Terres australes françaises
    # Note: NC and PF may retain specific processing for identifiers
}

# -------------------------------------------------------------------------
# Specific Identifiers for Flux 10
# -------------------------------------------------------------------------

# Territories where entities may not have a SIREN
# These specific identifiers are accepted in e-reporting flows (Flux 10)
SPECIFIC_IDENTIFIER_SCHEMES = {
    'NC': {
        'qualifier': '0228',
        'name': 'RIDET',
        'description': 'New Caledonia business identifier',
    },
    'PF': {
        'qualifier': '0229',
        'name': 'TAHITI',
        'description': 'French Polynesia business identifier',
    },
    'WF': {
        'qualifier': '0227',
        'name': 'WF_ID',
        'description': 'Wallis & Futuna business identifier',
    },
}

E_INVOICING_ZONES = {'metro', 'drom_einvoicing'}

# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------


def is_france_territory(country_code):
    """Check if a country code represents a French territory (France or DROM-COM)."""
    if not country_code:
        return False
    return country_code.upper() in ALL_FRANCE_TERRITORIES


def get_territory_type(country_code):
    """Get the territory type for a given country code."""
    if not country_code:
        return None

    code = country_code.upper()

    if code in FRANCE_METRO:
        return 'metro'
    elif code in DROM_E_INVOICING:
        return 'drom_einvoicing'
    elif code in DROM_E_REPORTING:
        return 'drom_ereporting'
    elif code in COM_TERRITORIES:
        return 'com'


def should_use_einvoicing(company_country, partner_country):
    """Determine if e-invoicing (Flux 1) should be used for a transaction."""
    comp_type = get_territory_type(company_country.code)
    part_type = get_territory_type(partner_country.code)
    # Both in e-invoicing zone
    return {comp_type, part_type}.issubset(E_INVOICING_ZONES)


def map_country_code_for_ppf(country_code):
    """Map a country code to the value that should be used in PPF XML flows."""
    if (country_code or '').upper() in COUNTRY_CODE_MAPPED_TO_FR:
        return 'FR'

    return country_code


def get_specific_identifier_scheme(country_code):
    """Get the specific identifier scheme for a territory (if any)."""
    if not country_code:
        return None

    return SPECIFIC_IDENTIFIER_SCHEMES.get(country_code.upper())
