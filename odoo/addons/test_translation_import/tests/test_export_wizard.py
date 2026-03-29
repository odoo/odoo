# -*- coding: utf-8 -*-

import base64
from odoo.tests import common, tagged


@tagged("post_install", "-at_install", "-standard", "nightly_export")
class TestTranslationFlow(common.TransactionCase):
    def test_export_source(self):
        """Export the source terms for every module and save it"""

        for module in self.env["ir.module.module"].search([("state", "=", "installed")]):
            export = self.env["base.language.export"].create({
                "lang": "__new__",
                "format": "po",
                "modules": [(6, 0, [module.id])]
            })
            export.act_getfile()
            pot_file = base64.b64decode(export.data)
            common.save_test_file(
                module.name, pot_file, prefix="i18n_", extension="pot",
                document_type="Source Terms for %s" % module.name,
                date_format="",
            )
