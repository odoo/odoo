# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Attachments List and Document Indexation',
    'version': '2.1',
    'category': 'Hidden/Tools',
    'description': """
Attachments list and document indexation
========================================
* Show attachment on the top of the forms
* Document Indexation: odt, pdf, xlsx, docx

The `pdfminer.six` Python library has to be installed in order to index PDF files
""",
    'depends': ['web'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'external_dependencies': [
        {'pypi': 'pdfminer.six', 'modules': ['pdfminer'], 'optional': True, 'apt': 'python3-pdfminer'},
        {'pypi': 'openpyxl', 'optional': True, 'apt': 'python3-openpyxl'},
    ],
}
