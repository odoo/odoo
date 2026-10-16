from odoo import fields, models


class PdpFlowSlice(models.Model):
    _name = 'l10n.fr.pdp.flow.slice'
    _description = 'PDP Flow Slice'
    _order = 'flow_id, slice_date, document_type'

    flow_id = fields.Many2one(
        comodel_name='l10n.fr.pdp.flow',
        string="Flow",
        required=True,
        ondelete='cascade',
    )
    slice_date = fields.Date(string="Date", required=True)
    document_type = fields.Selection(
        selection=[('sale', "Sale"), ('refund', "Refund")],
        string="Document Type",
        required=True,
        default='sale',
    )
    move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='l10n_fr_pdp_flow_slice_move_rel',
        column1='slice_id',
        column2='move_id',
        string="Moves",
        copy=False,
    )
    invalid_move_ids = fields.Many2many(
        comodel_name='account.move',
        relation='l10n_fr_pdp_flow_slice_invalid_rel',
        column1='slice_id',
        column2='move_id',
        string="Invalid Moves",
        copy=False,
    )
    state = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('ready', "Ready"),
            ('pending', "Sent"),
            ('done', "Completed"),
            ('error', "Error"),
        ],
        string="Status",
        default='draft',
        index=True,
    )
    payload = fields.Binary(string="Payload", attachment=True, copy=False)
    payload_filename = fields.Char(string="Filename", copy=False)
    payload_sha256 = fields.Char(string="Payload SHA-256", copy=False)
    transport_identifier = fields.Char(string="Transport Identifier", copy=False)
    transport_status = fields.Char(string="Transport Status", copy=False)
    transport_message = fields.Text(string="Transport Message", copy=False)

    def aggregate_state_to_flow(self):
        """Mirror slice states on the parent flow."""
        for flow in self.mapped('flow_id'):
            states = set(flow.slice_ids.mapped('state'))
            if 'error' in states:
                flow.state = 'error'
            elif 'pending' in states:
                flow.state = 'pending'
            elif 'done' in states:
                flow.state = 'done'
            elif 'ready' in states:
                flow.state = 'ready'
            elif states:
                flow.state = 'draft'
