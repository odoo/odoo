from odoo import _, api, fields, models


class L10nPtStockNoDocumentWarning(models.TransientModel):
    """
    Asked when Validate is pressed on transfers that would travel with a transport document but whose
    operation type has no AT series: validated, they leave without one. Validating anyway runs the
    Validate button again with the options it was pressed with.
    """
    _name = 'l10n.pt.stock.no.document.warning'
    _description = "Warning before validating transfers without a transport document"

    picking_ids = fields.Many2many('stock.picking', string="Transfers", readonly=True)
    message = fields.Text(compute='_compute_message')

    @api.depends('picking_ids')
    def _compute_message(self):
        for wizard in self:
            wizard.message = _(
                "%(transfers)s would travel with a transport document, but its operation type (%(operation_types)s) "
                "has no AT series to issue it in. Validated, the goods leave without a transport document, and "
                "the transfer keeps a note of it.",
                transfers=", ".join(wizard.picking_ids.mapped('name')),
                operation_types=", ".join(wizard.picking_ids.picking_type_id.mapped('display_name')),
            )

    def action_open_operation_types(self):
        """Open the operation types of the transfers, where their AT series is set."""
        self.ensure_one()
        return self.picking_ids.picking_type_id._get_records_action(name=_("Operation Types"), context={})

    def action_validate(self):
        """Validate the transfers the Validate button was pressed on, without asking again."""
        self.ensure_one()
        pickings = self.env['stock.picking'].browse(self.env.context.get('button_validate_picking_ids'))
        return pickings.with_context(l10n_pt_skip_no_document_warning=True).button_validate()
