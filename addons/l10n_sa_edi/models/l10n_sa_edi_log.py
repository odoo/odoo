from odoo import api, fields, models

from .l10n_sa_edi_document import L10N_SA_DOCUMENT_STATES


class L10nSaEdiLog(models.Model):
    _name = 'l10n_sa_edi.log'
    _description = 'ZATCA Log'
    _order = 'create_date desc, id desc'

    l10n_sa_edi_document_id = fields.Many2one(comodel_name='l10n_sa_edi.document')
    document_state = fields.Selection(related='l10n_sa_edi_document_id.state')
    state = fields.Selection(selection=L10N_SA_DOCUMENT_STATES)
    attachment_name = fields.Char()
    is_test = fields.Boolean()
    message = fields.Html(translate=True)

    # Only the latest log for a given invoice should be actionable, others are just historical records of previous attempts.
    is_latest_log = fields.Boolean(compute='_compute_is_latest_log')

    @api.depends('l10n_sa_edi_document_id.l10n_sa_edi_log_ids')
    def _compute_is_latest_log(self):
        for log in self:
            log.is_latest_log = log.l10n_sa_edi_document_id.l10n_sa_edi_log_ids[:1] == log

    def action_retry(self):
        self.ensure_one()
        resource = self.l10n_sa_edi_document_id.resource
        if resource._l10n_sa_get_alerts() or not resource._l10n_sa_is_phase_2_applicable():
            return self.l10n_sa_edi_document_id.resource._l10n_sa_handle_alerts()

        return self.l10n_sa_edi_document_id._l10n_sa_post_zatca_edi(True)
