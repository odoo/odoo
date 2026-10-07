from odoo import api, fields, models


class L10n_Tr_EdiDocument(models.Model):
    _inherit = 'l10n_tr_edi.document'
    # A received e-Dispatch is told apart by its supplier, stored with its XML.
    _rec_names_search = ['name', 'attachment_id.description']

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        index='btree_not_null',
        check_company=True,
        ondelete='cascade',
    )
    document_type = fields.Selection(
        selection_add=[('edispatch', "e-Dispatch"), ('edispatch_response', "e-Dispatch Response")],
        ondelete={'edispatch': 'cascade', 'edispatch_response': 'cascade'},
    )

    @api.depends('name', 'document_type', 'attachment_id.description')
    def _compute_display_name(self):
        super()._compute_display_name()
        for document in self.filtered(lambda d: d.document_type == 'edispatch' and d.attachment_id.description):
            document.display_name = f"{document.attachment_id.description} - {document.display_name}"

    def action_fetch_status(self):
        # EXTENDS 'l10n_tr_edi'
        super().action_fetch_status()
        # As the synchronize buttons of the transfer: only a sent e-Dispatch has a status to follow up, a received
        # one has its answer.
        self.filtered(lambda d: d.document_type == 'edispatch').picking_id.filtered(
            lambda picking: picking.picking_type_code == 'outgoing' and picking.l10n_tr_edi_send_status in {'sent', 'waiting'},
        ).action_l10n_tr_edi_fetch_status()
        self.filtered(lambda d: d.document_type == 'edispatch_response').picking_id.filtered(
            lambda picking: picking.l10n_tr_edi_response_status in {'not_sent', 'sent', 'waiting', 'error'},
        ).action_l10n_tr_edi_fetch_response_status()

    def action_open_picking(self):
        self.ensure_one()
        return self.picking_id._get_records_action()
