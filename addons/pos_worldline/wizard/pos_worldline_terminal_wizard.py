from odoo import fields, models


class PosWorldlineTerminalWizard(models.TransientModel):
    _name = "pos.worldline.terminal.wizard"
    _description = "Select a Worldline Terminal to connect"

    payment_method_id = fields.Many2one("pos.payment.method", required=True, ondelete="cascade")
    line_ids = fields.One2many("pos.worldline.terminal.wizard.line", "wizard_id")
    terminal_line_id = fields.Many2one("pos.worldline.terminal.wizard.line", string="Terminal", ui_domain="[('wizard_id', '=', id)]")

    def action_confirm(self):
        self.ensure_one()
        self.payment_method_id.worldline_terminal_id = self.terminal_line_id.name


class PosWorldlineTerminalWizardLine(models.TransientModel):
    _name = "pos.worldline.terminal.wizard.line"
    _description = "Detected Worldline Terminals"

    wizard_id = fields.Many2one("pos.worldline.terminal.wizard", required=True, ondelete="cascade")
    name = fields.Char("Terminal ID", required=True)
