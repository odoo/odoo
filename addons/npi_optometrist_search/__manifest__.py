# -*- coding: utf-8 -*-
{
    'name': 'NPI Optometrist Search',
    'version': '1.1',
    'category': 'Healthcare',
    'summary': 'Search for optometrists and ophthalmologists via the NPPES NPI Registry API',
    'description': """
Search NPI Registry for Eye Care Providers
============================================
Search the National Plan and Provider Enumeration System (NPPES) NPI Registry
for optometrists and ophthalmologists by name, state, or other criteria.
Each search runs for both provider types and combines results. Results show
provider type, name, NPI number, address, and taxonomy.
    """,
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'security/external_provider_access.xml',
        'views/npi_optometrist_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'external_dependencies': {
        'python': ['requests'],
    },
    'post_init_hook': 'post_init_hook',
}
