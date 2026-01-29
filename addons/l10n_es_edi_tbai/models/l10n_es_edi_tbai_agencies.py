# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


# ===== TicketBAI TAX AGENCY METADATA =====

def get_key(agency, key, is_test_env=True):
    """
    Helper method to retrieve specific data about certain agencies.
    Notable differences in structure, by key
    - Any key ending with '_':
    These keys have two variants: 'test' and 'prod'. The parameter `is_test_env` matters for those keys only.
    - 'xsd_url':
    Araba and Gipuzkoa each have a single URL pointing to a zip file (which may contain many XSDs)
    Bizkaia has two URLs for post/cancel XSDs: in that case a dict of strings is returned (instead of a single string)
    """
    urls = {
        'araba': URLS_ARABA,
        'bizkaia': URLS_BIZKAIA,
        'gipuzkoa': URLS_GIPUZKOA,
    }[agency]
    if key.endswith('_'):
        key += 'test' if is_test_env else 'prod'
    return urls[key]


URLS_ARABA = {
    'sigpolicy_url': 'https://ticketbai.araba.eus/tbai/sinadura/',
    'sigpolicy_digest': '4Vk3uExj7tGn9DyUCPDsV9HRmK6KZfYdRiW3StOjcQA=',
    'xsd_url': 'https://web.araba.eus/documents/105044/5608600/TicketBai12+%282%29.zip',
    'xsd_name': {
        'post': 'ticketBaiV1-2.xsd',
        'cancel': 'Anula_ticketBaiV1-2.xsd',
    },
    'post_url_test': 'https://pruebas-ticketbai.araba.eus/TicketBAI/v1/facturas/',
    'post_url_prod': 'https://ticketbai.araba.eus/TicketBAI/v1/facturas/',
    'qr_url_test': 'https://pruebas-ticketbai.araba.eus/tbai/qrtbai/',
    'qr_url_prod': 'https://ticketbai.araba.eus/tbai/qrtbai/',
    'cancel_url_test': 'https://pruebas-ticketbai.araba.eus/TicketBAI/v1/anulaciones/',
    'cancel_url_prod': 'https://ticketbai.araba.eus/TicketBAI/v1/anulaciones/',
}

URLS_BIZKAIA = {
    'sigpolicy_url': 'https://www.batuz.eus/fitxategiak/batuz/ticketbai/sinadura_elektronikoaren_zehaztapenak_especificaciones_de_la_firma_electronica_v1_0.pdf',
    'sigpolicy_digest': 'Quzn98x3PMbSHwbUzaj5f5KOpiH0u8bvmwbbbNkO9Es=',
    'xsd_url': {
        'post': 'https://www.batuz.eus/fitxategiak/batuz/ticketbai/ticketBaiV1-2-1.xsd',
        'cancel': 'https://www.batuz.eus/fitxategiak/batuz/ticketbai/Anula_ticketBaiV1-2-1.xsd',
    },
    'xsd_name': {
        'post': 'ticketBaiV1-2-1.xsd',
        'cancel': 'Anula_ticketBaiV1-2-1.xsd',
    },
    'post_url_test': 'https://pruesarrerak.bizkaia.eus/N3B4000M/aurkezpena',
    'post_url_prod': 'https://sarrerak.bizkaia.eus/N3B4000M/aurkezpena',
    'qr_url_test': 'https://batuz.eus/QRTBAI/',
    'qr_url_prod': 'https://batuz.eus/QRTBAI/',
    'cancel_url_test': 'https://pruesarrerak.bizkaia.eus/N3B4000M/aurkezpena',
    'cancel_url_prod': 'https://sarrerak.bizkaia.eus/N3B4000M/aurkezpena',
}

URLS_GIPUZKOA = {
    'sigpolicy_url': 'https://www.gipuzkoa.eus/TicketBAI/signature',
    'sigpolicy_digest': '6NrKAm60o7u62FUQwzZew24ra2ve9PRQYwC21AM6In0=',
    'xsd_url': 'https://www.gipuzkoa.eus/documents/2456431/13761107/Esquemas+de+archivos+XSD+de+env%C3%ADo+y+anulaci%C3%B3n+de+factura_1_2.zip/2d116f8e-4d3a-bff0-7b03-df1cbb07ec52',
    'xsd_name': {
        'post': 'ticketBaiV1-2-1.xsd',
        'cancel': 'Anula_ticketBaiV1-2-1.xsd',
    },
    'post_url_test': 'https://tbai-prep.egoitza.gipuzkoa.eus/WAS/HACI/HTBRecepcionFacturasWEB/rest/recepcionFacturas/alta',
    'post_url_prod': 'https://tbai-z.egoitza.gipuzkoa.eus/sarrerak/alta',
    'qr_url_test': 'https://tbai.prep.gipuzkoa.eus/qr/',
    'qr_url_prod': 'https://tbai.egoitza.gipuzkoa.eus/qr/',
    'cancel_url_test': 'https://tbai-prep.egoitza.gipuzkoa.eus/WAS/HACI/HTBRecepcionFacturasWEB/rest/recepcionFacturas/anulacion',
    'cancel_url_prod': 'https://tbai-z.egoitza.gipuzkoa.eus/sarrerak/baja',
}
