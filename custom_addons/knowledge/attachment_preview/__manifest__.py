# Copyright 2014 Therp BV (<http://therp.nl>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Preview attachments",
    "version": "19.0.1.0.0",
    "author": "Therp BV," "Onestein," "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/knowledge",
    "license": "AGPL-3",
    "summary": "Preview attachments supported by Viewer.js",
    "category": "Knowledge Management",
    "depends": ["web", "mail"],
    "data": [],
    "qweb": [],
    "assets": {
        "web._assets_primary_variables": [],
        "web.assets_backend": [
            "attachment_preview/static/src/js/attachmentPreviewWidget.esm.js",
            "attachment_preview/static/src/js/utils.esm.js",
            "attachment_preview/static/src/js/mail_core/attachment_list.esm.js",
            "attachment_preview/static/src/js/web_views/fields/binary_field.esm.js",
            "attachment_preview/static/src/js/web_views/form/form_compiler.esm.js",
            "attachment_preview/static/src/js/web_views/form/form_controller.esm.js",
            "attachment_preview/static/src/js/web_views/form/form_renderer.esm.js",
            "attachment_preview/static/src/scss/attachment_preview.scss",
            "attachment_preview/static/src/xml/attachment_preview.xml",
        ],
    },
    "installable": True,
}

