# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import fields, models
from odoo.addons.l10n_ph import utils


class Generate2307Wizard(models.TransientModel):
    _name = "l10n_ph_2307.wizard"
    _description = "Exports 2307 data to a XLS file."

    moves_to_export = fields.Many2many("account.move", string="Joural To Include")
    xls_file = fields.Binary(
        "Generated file",
        help="Technical field used to temporarily hold the generated XLS file before its downloaded."
    )

    def action_generate(self):
        """ Generate a xls format file for importing to
        https://bir-excel-uploader.com/excel-file-to-bir-dat-format/#bir-form-2307-settings.
        This website will then generate a BIR 2307 format excel file for uploading to the
        PH government.
        """
        self.ensure_one()

        self.xls_file = base64.b64encode(utils._export_bir_2307('Form2307', self.moves_to_export, file_format='xls'))

        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": f"/web/content?model=l10n_ph_2307.wizard&download=true&field=xls_file&filename=Form_2307.xls&id={self.id}",
        }
