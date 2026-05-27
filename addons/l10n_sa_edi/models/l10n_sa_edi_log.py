from odoo import fields, models

from .l10n_sa_edi_document import L10N_SA_DOCUMENT_STATES


class L10nSaEdiLog(models.Model):
    _name = 'l10n_sa_edi.log'
    _order = 'create_date desc'
    _description = 'ZATCA Log'

    account_move_id = fields.Many2one('account.move', ondelete='cascade')
    l10n_sa_edi_document_id = fields.Many2one(comodel_name='l10n_sa_edi.document')
    document_state = fields.Selection(related='l10n_sa_edi_document_id.state')
    state = fields.Selection(selection=L10N_SA_DOCUMENT_STATES)
    attachment_name = fields.Char()
    is_test = fields.Boolean()
    message = fields.Html(translate=True)

    def action_retry(self):
        self.ensure_one()
        resource = self.l10n_sa_edi_document_id.resource
        if resource._l10n_sa_get_alerts() or not resource._l10n_sa_is_phase_2_applicable():
            return self.resource._l10n_sa_handle_alerts()

        if self.state == 'rejected':  # If retry from a rejected state, we create a new document, storing the old one for traceability purposes.
            resource._l10n_sa_edi_create_document()
        return resource.l10n_sa_edi_document_id._l10n_sa_post_zatca_edi(True)
