# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Uom(models.Model):
    _inherit = 'uom.uom'

    def _unprotected_uom_xml_ids(self):
        # Override
        # When timesheet App is installed, we also need to protect the hour UoM
        # from deletion (and warn in case of modification)
        return [
            "product_uom_dozen",
        ]

    # widget used in the webclient when this unit is the one used to encode timesheets.
    timesheet_widget = fields.Char("Widget", export_string_translation=False)
