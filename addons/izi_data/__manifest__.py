# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
# noinspection PyUnresolvedReferences,SpellCheckingInspection
{
    "name": """Analytic Data Query""",
    "summary": """IZI Module to Handle Data Query. Dependency For IZI Dashboard by IZI""",
    "category": "Reporting",
    "version": "16.0.5.0.1",
    "development_status": "Alpha",  # Options: Alpha|Beta|Production/Stable|Mature
    "auto_install": False,
    "installable": True,
    "application": False,
    "author": "IZI PT Solusi Usaha Mudah",
    "support": "admin@iziapp.id",
    "website": "https://www.iziapp.id",
    "license": "OPL-1",
    "images": [
        'static/description/banner.jpg'
    ],

    "price": 0.00,
    "currency": "USD",

    "depends": [
        # odoo addons
        'base',
        # third party addons

        # developed addons
    ],
    "data": [
        # group
        'security/res_groups.xml',

        # data
        'data/izi_table_field_mapping_db_odoo.xml',
        'data/izi_analysis_filter_operator_db_odoo.xml',

        # global action
        # 'views/action/action.xml',

        # view
        'views/common/izi_data_source.xml',
        'views/common/izi_table.xml',
        'views/common/izi_analysis.xml',
        'views/common/ir_attachment.xml',
        'views/common/ir_cron.xml',
        'views/common/izi_kpi.xml',
        'views/common/izi_kpi_line.xml',

        # wizard

        # report paperformat
        # 'data/report_paperformat.xml',

        # report template
        # 'views/report/report_template_model_name.xml',

        # report action
        # 'views/action/action_report.xml',

        # assets
        # 'views/assets.xml',

        # onboarding action
        # 'views/action/action_onboarding.xml',

        # action menu
        'views/action/action_menu.xml',

        # action onboarding
        # 'views/action/action_onboarding.xml',

        # menu
        'views/menu.xml',

        # security
        'security/ir.model.access.csv',
        # 'security/ir.rule.csv',

        # data
    ],
    "demo": [
        # 'demo/demo.xml',
    ],
    "qweb": [
        # "static/src/xml/{QWEBFILE1}.xml",
    ],

    "post_load": None,
    # "pre_init_hook": "pre_init_hook",
    # "post_init_hook": "post_init_hook",
    "uninstall_hook": None,

    "external_dependencies": {"python": [
        "requests",
        "xlsxwriter",
        "sqlparse",
    ], "bin": []},
    # "live_test_url": "",
    # "demo_title": "{MODULE_NAME}",
    # "demo_addons": [
    # ],
    # "demo_addons_hidden": [
    # ],
    # "demo_url": "DEMO-URL",
    # "demo_summary": "{SHORT_DESCRIPTION_OF_THE_MODULE}",
    # "demo_images": [
    #    "images/MAIN_IMAGE",
    # ]
}
