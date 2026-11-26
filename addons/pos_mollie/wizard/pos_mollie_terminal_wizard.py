from odoo import api, fields, models


class PosMollieTerminalWizard(models.TransientModel):
    _name = "pos.mollie.terminal.wizard"
    _description = "Select a Mollie Terminal to connect"

    payment_method_id = fields.Many2one("pos.payment.method", required=True, ondelete="cascade")
    line_ids = fields.One2many("pos.mollie.terminal.wizard.line", "wizard_id")
    terminal_line_id = fields.Many2one("pos.mollie.terminal.wizard.line", string="Terminal", ui_domain="[('wizard_id', '=', id)]")

    def action_confirm(self):
        self.ensure_one()
        self.payment_method_id.mollie_terminal_id = self.terminal_line_id.name


class PosMollieTerminalWizardLine(models.TransientModel):
    _name = "pos.mollie.terminal.wizard.line"
    _description = "Detected Mollie Terminals"

    wizard_id = fields.Many2one("pos.mollie.terminal.wizard", required=True, ondelete="cascade")
    name = fields.Char("Terminal ID", required=True)
    description = fields.Char()
    serial_number = fields.Char()

    @api.depends("name", "description", "serial_number")
    def _compute_display_name(self):
        for line in self:
            details = " - ".join(filter(None, [line.description, line.serial_number]))
            line.display_name = f"{line.name} ({details})" if details else line.name
