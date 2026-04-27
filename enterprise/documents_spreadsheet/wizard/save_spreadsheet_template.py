# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

class SaveSpreadsheetTemplate(models.TransientModel):
    _name = 'save.spreadsheet.template'
    _inherit = "spreadsheet.mixin"
    _description= "Spreadsheet Template Save Wizard"

    template_name = fields.Char(required=True)

    def save_template(self):
        self.ensure_one()
        template = self.env['spreadsheet.template'].create({
            'name': self.template_name,
            'spreadsheet_data': self.spreadsheet_data,
            'thumbnail': self.thumbnail,
        })
        template._delete_comments_from_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('"%s" saved as template', self.template_name),
                'sticky': False,
                'type': 'info',
            }
        }
