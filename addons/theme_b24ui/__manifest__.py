# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Theme B24 UI',
    'version': '1.0',
    'category': 'Theme/Backend',
    'summary': 'Tema visual do backend inspirado no design system do b24ui-clone (Bitrix24)',
    'description': """
Sobrescreve as variáveis de cor, raio de borda e tipografia do backend do Odoo
para aproximar a aparência do design system do b24ui-clone, sem alterar a
arquitetura ou a lógica do webclient (OWL).
""",
    'depends': ['web'],
    'assets': {
        'web._assets_primary_variables': [
            ('before', 'web/static/src/scss/primary_variables.scss',
             'theme_b24ui/static/src/scss/primary_variables.scss'),
        ],
        'web._assets_secondary_variables': [
            ('before', 'web/static/src/scss/secondary_variables.scss',
             'theme_b24ui/static/src/scss/secondary_variables.scss'),
        ],
        'web.assets_backend': [
            'theme_b24ui/static/src/scss/backend_overrides.scss',
        ],
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
