{
    "name": "Barcode",
    "version": "2.1",
    "category": "Supply Chain/Inventory",
    "summary": "Scan and Parse Barcodes",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "web",
    ],
    "data": [
        "security/ir.access.csv",
        "data/barcodes_data.xml",
        "views/barcodes_view.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "barcodes/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "barcodes/static/tests/*.test.js",
            "barcodes/static/tests/conformance_vectors.js",
            "barcodes/static/tests/barcode_test_helpers.js",
        ],
    },
    "post_init_hook": "_update_default_nomenclature",
}
