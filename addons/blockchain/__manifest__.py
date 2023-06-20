{
    'name': 'Blockchain',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'description': """
This module allows Odoo models to have an inalterable blockchain (blockchain). The
records will be hashed in a linked chain as to provide inalterability. One can easily
reimplement some methods to get this feature working for a specific model. This is specially
useful to verify the integrity of the records and be sure that after the hash is
computed, we cannot modify important fields that would break the integrity of the 
hashing chain.
""",
    'depends': [
        'base'
    ],
    'data': [
        'report/report_blockchain_integrity.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
