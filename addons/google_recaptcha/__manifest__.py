# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Google reCAPTCHA integration',
    'category': 'Hidden',
    'version': '1.0',
    'description': """
        This module implements reCaptchaV3 so that you can prevent bot spam on your public modules.
    """,
    'depends': ['base_setup'],
    'data': [
        'views/res_config_settings_view.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'google_recaptcha/static/src/scss/recaptcha.scss',
            'google_recaptcha/static/src/js/recaptcha.js',
            # TODO remove next line in master, it was kept here as part of a
            # stable fix in stable but is unused in the current codebase.
            'google_recaptcha/static/src/xml/recaptcha.xml',
        ],
        'web.assets_backend': [
            # TODO we may want to consider moving that file in website instead
            # of here and/or adding it in the "website.assets_wysiwyg" bundle,
            # which is lazy loaded.
            'google_recaptcha/static/src/xml/recaptcha.xml',
        ],
    },
    'license': 'LGPL-3',
}
