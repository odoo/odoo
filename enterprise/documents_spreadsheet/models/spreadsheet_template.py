# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class SpreadsheetTemplate(models.Model):
    _name = "spreadsheet.template"
    _inherit = "spreadsheet.mixin"
    _description = "Spreadsheet Template"
    _order = "sequence"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=100)
    file_name = fields.Char(compute="_compute_file_name")

    @api.depends("name")
    def _compute_file_name(self):
        for template in self:
            template.file_name = f"{template.name}.osheet.json"

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for template, vals in zip(self, vals_list):
            vals['name'] = default.get("name", _("%s (copy)", template.name))
        return vals_list

    def action_edit_template(self):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "action_open_template",
            "params": {
                "spreadsheet_id": self.id,
            },
        }

    def action_create_spreadsheet(self, document_vals=None):
        if document_vals is None:
            document_vals = {}
        self.ensure_one()
        spreadsheet = self.env["documents.document"].create({
            "name": self.name,
            "mimetype": "application/o-spreadsheet",
            "handler": "spreadsheet",
            "spreadsheet_data": self.spreadsheet_data,
            **document_vals,
        })
        spreadsheet.spreadsheet_snapshot = self.spreadsheet_snapshot
        self._copy_revisions_to(spreadsheet)
        spreadsheet._delete_comments_from_data()

        update_locale_command = {
            "type": "UPDATE_LOCALE",
            "locale": self.env["res.lang"]._get_user_spreadsheet_locale(),
        }
        spreadsheet._dispatch_command(update_locale_command)

        return {
            "type": "ir.actions.client",
            "tag": "action_open_spreadsheet",
            "params": {
                "spreadsheet_id": spreadsheet.id,
            },
        }

    def action_open_spreadsheet(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'action_open_template',
            'params': {
                'spreadsheet_id': self.id,
            }
        }
