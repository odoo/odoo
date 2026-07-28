# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import markupsafe
from odoo import _, api, fields, models, release


# === TBAI license values ===
L10N_ES_TBAI_LICENSE_DICT = {
    'production': {
        'license_name': _('Production license'),  # all agencies
        'license_number': 'TBAIGI5A266A7CCDE1EC',
        'license_nif': 'N0251909H',
        'software_name': 'Odoo SA',
        'software_version': release.version,
    },
    'araba': {
        'license_name': _('Test license (Araba)'),
        'license_number': 'TBAIARbjjMClHKH00849',
        'license_nif': 'N0251909H',
        'software_name': 'Odoo SA',
        'software_version': release.version,
    },
    'bizkaia': {
        'license_name': _('Test license (Bizkaia)'),
        'license_number': 'TBAIBI00000000PRUEBA',
        'license_nif': 'A99800005',
        'software_name': 'SOFTWARE GARANTE TICKETBAI PRUEBA',
        'software_version': '1.0',
    },
    'gipuzkoa': {
        'license_name': _('Test license (Gipuzkoa)'),
        'license_number': 'TBAIGIPRE00000000965',
        'license_nif': 'N0251909H',
        'software_name': 'Odoo SA',
        'software_version': release.version,
    },
}

class ResCompany(models.Model):
    _inherit = 'res.company'

    # === TBAI config ===
    l10n_es_tbai_tax_agency = fields.Selection(
        string="Tax Agency for TBAI",
        selection=[
            ('araba', "Hacienda Foral de Araba"),  # es-vi (region code)
            ('bizkaia', "Hacienda Foral de Bizkaia"),  # es-bi
            ('gipuzkoa', "Hacienda Foral de Gipuzkoa"),  # es-ss
        ],
    )
    l10n_es_tbai_license_html = fields.Html(
        string="TicketBAI license",
        compute='_compute_l10n_es_tbai_license_html',
    )

    # === TBAI CHAIN HEAD ===
    l10n_es_tbai_chain_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string='TicketBai account.move chain sequence',
        readonly=True,
        copy=False,
    )

    @api.depends('country_id', 'l10n_es_edi_test_env', 'l10n_es_tbai_tax_agency')
    def _compute_l10n_es_tbai_license_html(self):
        for company in self:
            license_dict = company._get_l10n_es_tbai_license_dict()
            if license_dict:
                license_dict.update({
                    'tr_nif': _('Licence NIF'),
                    'tr_number': _('Licence number'),
                    'tr_name': _('Software name'),
                    'tr_version': _('Software version')
                })
                company.l10n_es_tbai_license_html = markupsafe.Markup('''
<strong>{license_name}</strong><br/>
<p>
<strong>{tr_nif}: </strong>{license_nif}<br/>
<strong>{tr_number}: </strong>{license_number}<br/>
<strong>{tr_name}: </strong>{software_name}<br/>
<strong>{tr_version}: </strong>{software_version}<br/>
</p>''').format(**license_dict)
            else:
                company.l10n_es_tbai_license_html = markupsafe.Markup('''
<strong>{tr_no_license}</strong>''').format(tr_no_license=_('TicketBAI is not configured'))

    def _get_l10n_es_tbai_license_dict(self):
        self.ensure_one()
        if self.country_code == 'ES' and self.l10n_es_tbai_tax_agency:
            if self.l10n_es_edi_test_env:  # test env: each agency has its test license
                license_key = self.l10n_es_tbai_tax_agency
            else:  # production env: only one license
                license_key = 'production'
            return L10N_ES_TBAI_LICENSE_DICT[license_key]
        else:
            return {}

    def _get_l10n_es_tbai_next_chain_index(self):
        if not self.l10n_es_tbai_chain_sequence_id:
            self_sudo = self.sudo()
            self_sudo.l10n_es_tbai_chain_sequence_id = self_sudo.env['ir.sequence'].create({
                'name': f'TicketBAI account move sequence for {self.name} (id: {self.id})',
                'code': f'l10n_es.edi.tbai.account.move.{self.id}',
                'implementation': 'no_gap',
                'company_id': self.id,
            })
        return self.l10n_es_tbai_chain_sequence_id.next_by_id()

    def _get_l10n_es_tbai_last_posted_invoice(self, being_posted=False):
        """
        Returns the last invoice posted to this company's chain.
        That invoice may have been received by the govt or not (eg. in case of a timeout).
        Only upon confirmed reception/refusal of that invoice can another one be posted.
        :param being_posted: next invoice to be posted on the chain, ignored in search domain
        """
        domain = [
            ('l10n_es_tbai_chain_index', '!=', 0),
            ('company_id', '=', self.id)
        ]
        if being_posted:
            domain.append(('l10n_es_tbai_chain_index', '!=', being_posted.l10n_es_tbai_chain_index))
            # NOTE: being_posted may not have a chain index at all (if being posted for the first time)
        return self.env['account.move'].search(domain, limit=1, order='l10n_es_tbai_chain_index desc')
