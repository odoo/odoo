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
COUNTRY_CODE_TO_FR_MAPPING = {
    'GP': 'FR',  # Guadeloupe
    'MQ': 'FR',  # Martinique
    'GF': 'FR',  # Guyane
    'RE': 'FR',  # La Réunion
    'YT': 'FR',  # Mayotte
    'BL': 'FR',  # Saint-Barthélemy
    'MF': 'FR',  # Saint-Martin
    'PM': 'FR',  # Saint-Pierre-et-Miquelon
    'WF': 'FR',  # Wallis-et-Futuna
    'TF': 'FR',  # Terres australes françaises
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

# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------


def is_france_territory(country_code):
    """Check if a country code represents a French territory (France or DROM-COM)."""
    if not country_code:
        return False
    return country_code.upper() in ALL_FRANCE_TERRITORIES


def is_drom_com(country_code):
    """Check if a country code represents a DROM-COM territory."""
    if not country_code:
        return False
    return country_code.upper() in ALL_DROM_COM


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

    return None


def should_use_einvoicing(company_country, partner_country):
    """Determine if e-invoicing (Flux 1) should be used for a transaction."""
    if not company_country or not partner_country:
        return False

    comp_type = get_territory_type(company_country)
    part_type = get_territory_type(partner_country)

    # Both must be French territories
    if not comp_type or not part_type:
        return False

    # E-invoicing zones: Metro + DROM e-invoicing group
    einvoicing_zones = {'metro', 'drom_einvoicing'}

    # Both in e-invoicing zone
    return comp_type in einvoicing_zones and part_type in einvoicing_zones


def map_country_code_for_ppf(country_code):
    """Map a country code to the value that should be used in PPF XML flows."""
    if not country_code:
        return country_code

    return COUNTRY_CODE_TO_FR_MAPPING.get(country_code.upper(), country_code)


def get_specific_identifier_scheme(country_code):
    """Get the specific identifier scheme for a territory (if any)."""
    if not country_code:
        return None

    return SPECIFIC_IDENTIFIER_SCHEMES.get(country_code.upper())


def get_transaction_flow_type(company_country, partner_country, partner_vat):
    """Determine the type of transaction flow for reporting purposes."""
    # No VAT = B2C domestic
    if not partner_vat or partner_vat == '/':
        return 'b2c'

    # If no country info, cannot determine
    if not company_country or not partner_country:
        return False

    comp_type = get_territory_type(company_country)
    part_type = get_territory_type(partner_country)

    # One party outside French territories = International
    if not comp_type or not part_type:
        return 'international'

    # Both parties in e-invoicing zones = Domestic B2B (excluded from Flux 10)
    if should_use_einvoicing(company_country, partner_country):
        return False

    # All other cases: International
    return 'international'


def is_b2b_transaction(partner_vat):
    """Check if a transaction is B2B based on partner VAT."""
    return bool(partner_vat and partner_vat != '/')


def get_drom_com_info():
    """Get comprehensive information about DROM-COM territories."""
    return {
        'GP': {'name': 'Guadeloupe', 'type': 'drom_einvoicing', 'vat_regime': 'similar_to_metro'},
        'MQ': {'name': 'Martinique', 'type': 'drom_einvoicing', 'vat_regime': 'similar_to_metro'},
        'RE': {'name': 'La Réunion', 'type': 'drom_einvoicing', 'vat_regime': 'similar_to_metro'},
        'GF': {'name': 'Guyane Française', 'type': 'drom_ereporting', 'vat_regime': 'specific_export'},
        'YT': {'name': 'Mayotte', 'type': 'drom_ereporting', 'vat_regime': 'specific_export'},
        'BL': {'name': 'Saint-Barthélemy', 'type': 'com', 'vat_regime': 'non_domestic'},
        'MF': {'name': 'Saint-Martin', 'type': 'com', 'vat_regime': 'non_domestic'},
        'PM': {'name': 'Saint-Pierre-et-Miquelon', 'type': 'com', 'vat_regime': 'non_domestic'},
        'PF': {'name': 'Polynésie Française', 'type': 'com', 'vat_regime': 'non_domestic', 'identifier': 'TAHITI'},
        'WF': {'name': 'Wallis-et-Futuna', 'type': 'com', 'vat_regime': 'non_domestic', 'identifier': 'WF_ID'},
        'TF': {'name': 'TAAF', 'type': 'com', 'vat_regime': 'non_domestic'},
        'NC': {'name': 'Nouvelle-Calédonie', 'type': 'com', 'vat_regime': 'non_domestic', 'identifier': 'RIDET'},
        'FR': {'name': 'France Métropolitaine', 'type': 'metro', 'vat_regime': 'standard'},
    }
