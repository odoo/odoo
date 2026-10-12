from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VerifactuIssuer(models.Model):
    _name = 'l10n_es_edi_verifactu.issuer'
    _description = 'Veri*Factu Issuer'

    _unique_issuer_per_obligado = models.Constraint(
        'UNIQUE(company_id, obligado_partner_id)',
        "There can only be one virtual SIF per company and obligado.",
    )

    company_id = fields.Many2one(comodel_name='res.company', required=True)
    obligado_partner_id = fields.Many2one(comodel_name='res.partner', required=True)
    next_batch_time = fields.Datetime()
    chain_sequence_id = fields.Many2one(comodel_name='ir.sequence')

    def _get_or_create(self, company, obligado_partner):
        issuer = self.sudo().search([
            ('company_id', '=', company.id),
            ('obligado_partner_id', '=', obligado_partner.id),
        ], limit=1)
        if not issuer:
            issuer = self.sudo().create({
                'company_id': company.id,
                'obligado_partner_id': obligado_partner.id,
            })
        return issuer

    def _get_chain_sequence(self):
        self.ensure_one()
        if not self.chain_sequence_id:
            sequence = self.env['ir.sequence'].sudo().create({
                'name': _(
                    "Veri*Factu Chain Sequence for %(company)s / %(partner)s (%(pid)s)",
                    company=self.company_id.name,
                    partner=self.obligado_partner_id.name,
                    pid=self.obligado_partner_id.id,
                ),
                'code': f'l10n_es_edi_verifactu.document.{self.company_id.id}.{self.obligado_partner_id.id}',
                'implementation': 'no_gap',
                'company_id': self.company_id.id,
            })
            self.sudo().chain_sequence_id = sequence
        return self.chain_sequence_id

    def _get_last_document(self):
        self.ensure_one()
        return self.env['l10n_es_edi_verifactu.document'].search([
            ('chain_index', '!=', False),
            ('company_id', '=', self.company_id.id),
            ('obligado_partner_id', '=', self.obligado_partner_id.id),
        ], order='chain_index DESC', limit=1)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_no_chained_documents(self):
        for issuer in self:
            has_documents = self.env['l10n_es_edi_verifactu.document'].sudo().search_count([
                ('company_id', '=', issuer.company_id.id),
                ('obligado_partner_id', '=', issuer.obligado_partner_id.id),
                ('chain_index', '!=', False),
            ], limit=1)
            if has_documents:
                raise UserError(_(
                    "Cannot delete the Veri*Factu SIF for '%(partner)s': "
                    "it has chained documents that must be preserved for audit purposes.",
                    partner=issuer.obligado_partner_id.display_name,
                ))
