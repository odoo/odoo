from odoo import api, fields, models

from .l10n_sa_edi_document import L10N_SA_DOCUMENT_STATES


class L10nSaEdiLog(models.Model):
    _name = 'l10n_sa_edi.log'
    _order = 'create_date desc'
    _description = 'ZATCA Log'

    l10n_sa_edi_document_id = fields.Many2one(comodel_name='l10n_sa_edi.document')
    document_state = fields.Selection(related='l10n_sa_edi_document_id.state')
    l10n_sa_edi_chain_head_id = fields.Many2one(comodel_name='l10n_sa_edi.document', compute='_compute_l10n_sa_edi_chain_head_id')
    state = fields.Selection(selection=L10N_SA_DOCUMENT_STATES)
    attachment_name = fields.Char()
    is_test = fields.Boolean()
    message = fields.Html(translate=True)

    @api.depends('l10n_sa_edi_document_id.l10n_sa_edi_chain_head_id.state')
    def _compute_l10n_sa_edi_chain_head_id(self):
        for record in self:
            record.l10n_sa_edi_chain_head_id = record.l10n_sa_edi_document_id.l10n_sa_edi_chain_head_id.filtered(lambda rec: rec.state not in ['accepted', 'warning', 'rejected'])

    def action_retry(self):
        self.ensure_one()
        resource = self.l10n_sa_edi_document_id.resource
        if resource._l10n_sa_get_alerts() or not resource._l10n_sa_is_phase_2_applicable():
            return self.l10n_sa_edi_document_id.resource._l10n_sa_handle_alerts()

        return self.l10n_sa_edi_document_id._l10n_sa_post_zatca_edi(True)

    def action_open_chain_head(self):
        self.ensure_one()
        return self.l10n_sa_edi_chain_head_id.resource._get_records_action()
