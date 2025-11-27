from odoo import fields, models, _


class PdpSendWizard(models.TransientModel):
    _name = 'l10n.fr.pdp.send.wizard'
    _description = 'Send PDP Flow Wizard'

    flow_id = fields.Many2one(
        comodel_name='l10n.fr.pdp.flow',
        required=True,
        ondelete='cascade',
        default=lambda self: self.env.context.get('default_flow_id'),
    )
    warning = fields.Text(
        readonly=True,
        default=lambda self: _("Some invoices were excluded due to validation errors."),
    )

    def action_view_errors(self):
        """Open list of invalid invoices."""
        self.ensure_one()
        return self.flow_id.action_view_error_moves()

    def action_send_anyway(self):
        """Send flow excluding invalid invoices."""
        self.ensure_one()
        if not self.flow_id.name:
            self.flow_id._update_reference_name()
        return self.flow_id.with_context(ignore_error_invoices=True).action_send_from_ui()
