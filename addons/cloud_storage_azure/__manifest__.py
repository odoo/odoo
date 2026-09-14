{
    "name": "Cloud Storage Azure",
    "version": "1.1",
    "category": "Hidden/Tools",
    "summary": "Store chatter attachments in the Azure cloud",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "credential",
        "cloud_storage",
    ],
    "data": [
        "views/settings.xml",
    ],
    "uninstall_hook": "uninstall_hook",
}
