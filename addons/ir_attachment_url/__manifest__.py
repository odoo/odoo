# Copyright 2020 Ivan Yelizariev <https://twitter.com/yelizariev>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
{
    "name": "Attachment Url",
    "summary": """Use attachment URL and upload data to external storage""",
    "category": "Tools",
    "images": ["images/ir_attachment_url.jpg"],
    "version": "14.0.3.0.0",
    "application": False,
    "author": "IT-Projects LLC, Ildar Nasyrov",
    "website": "https://twitter.com/OdooFree",
    "license": "LGPL-3",
    "depends": ["web"],
    "external_dependencies": {"python": [], "bin": []},
    "data": ["views/ir_attachment.xml"],
    "qweb": [],
    "demo": [],
    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
    "auto_install": False,
    "installable": True,
}
