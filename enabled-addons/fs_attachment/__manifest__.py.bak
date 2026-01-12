# Copyright 2017-2021 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)


{
    "name": "Base Attachment Object Store",
    "summary": "Store attachments on external object store",
    "version": "18.0.2.2.0",
    "author": "Camptocamp, ACSONE SA/NV, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "development_status": "Beta",
    "category": "Knowledge Management",
    "depends": ["fs_storage"],
    "website": "https://github.com/OCA/storage",
    "data": [
        "security/fs_file_gc.xml",
        "views/fs_storage.xml",
    ],
    "external_dependencies": {"python": ["python_slugify", "fsspec>=2025.3.0"]},
    "installable": True,
    "auto_install": False,
    "maintainers": ["lmignon"],
    "pre_init_hook": "pre_init_hook",
}
