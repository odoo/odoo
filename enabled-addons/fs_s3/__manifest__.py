# Copyright 2023 ACSONE SA/NV
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "FS S3 Storage",
    "summary": "Implement S3 Storage",
    "version": "19.0.1.0.0",
    "category": "FS Storage",
    "website": "https://github.com/OCA/storage",
    "author": "ACSONE SA/NV, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "installable": True,
    "depends": ["fs_storage"],
    "data": [
        "views/fs_storage_view.xml",
    ],
    "external_dependencies": {
        "python": [
            "fsspec>=2024.5.0",
            "s3fs>=2024.5.0",
        ]
    },
}
