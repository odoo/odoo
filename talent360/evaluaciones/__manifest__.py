{
    "name": "Evaluaciones",
    "application": True,
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "security/rules.xml",
        "views/evaluaciones_views.xml",
        "views/evaluaciones_menus.xml",
        "views/reportes_templates.xml",
    ],
    "depends": ["base", "mail"],
    "assets": {
        "evaluaciones.evaluaciones_assets": [
            ("include", "web.chartjs_lib"),
            "evaluaciones/static/src/js/survey_print.js",
            "evaluaciones/static/src/js/survey_result.js",
            ("include", "web._assets_helpers"),
            ("include", "web._assets_frontend_helpers"),
            "web/static/src/scss/pre_variables.scss",
            "web/static/lib/bootstrap/scss/_variables.scss",
            "evaluaciones/static/src/scss/survey_templates_form.scss",
            "evaluaciones/static/src/scss/survey_templates_results.scss",
        ],
    },
}
