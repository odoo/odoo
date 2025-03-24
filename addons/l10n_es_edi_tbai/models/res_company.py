# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import markupsafe
import re

from odoo import api, fields, models, release
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__)

# === TBAI license values ===
L10N_ES_TBAI_LICENSE_DICT = {
    'production': {
        'license_name': _lt('Production license'),  # all agencies
        'license_number': 'TBAIGI5A266A7CCDE1EC',
        'license_nif': 'N0251909H',
        'software_name': 'Odoo SA',
        'software_version': release.version,
    },
    'araba': {
        'license_name': _lt('Test license (Araba)'),
        'license_number': 'TBAIARbjjMClHKH00849',
        'license_nif': 'N0251909H',
        'software_name': 'Odoo SA',
        'software_version': release.version,
    },
    'bizkaia': {
        'license_name': _lt('Test license (Bizkaia)'),
        'license_number': 'TBAIBI00000000PRUEBA',
        'license_nif': 'A99800005',
        'software_name': 'SOFTWARE GARANTE TICKETBAI PRUEBA',
        'software_version': '1.0',
    },
    'gipuzkoa': {
        'license_name': _lt('Test license (Gipuzkoa)'),
        'license_number': 'TBAIGIPRE00000000965',
        'license_nif': 'N0251909H',
        'software_name': 'Odoo SA',
        'software_version': release.version,
    },
}

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_tbai_certificate_id = fields.Many2one(
        string="Certificate (TicketBAI)",
        store=True,
        readonly=False,
        comodel_name='certificate.certificate',
        compute="_compute_l10n_es_tbai_certificate",
    )
    l10n_es_tbai_certificate_ids = fields.One2many(
        comodel_name='certificate.certificate',
        inverse_name='company_id',
        domain=[('scope', '=', 'tbai')],
    )

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

    l10n_es_tbai_test_env = fields.Boolean(
        string="TBAI Test Mode",
        help="Use the test environment for TicketBAI",
        default=True,
    )

    l10n_es_tbai_is_enabled = fields.Boolean(compute='_compute_l10n_es_tbai_is_enabled')

    @api.depends('country_id', 'l10n_es_tbai_tax_agency')
    def _compute_l10n_es_tbai_is_enabled(self):
        for company in self:
            company.l10n_es_tbai_is_enabled = company.country_code == 'ES' and company.l10n_es_tbai_tax_agency

    @api.depends('country_id', 'l10n_es_tbai_certificate_ids')
    def _compute_l10n_es_tbai_certificate(self):
        for company in self:
            if company.country_code == 'ES':
                company.l10n_es_tbai_certificate_id = self.env['certificate.certificate'].search(
                    [('company_id', '=', company.id), ('is_valid', '=', True), ('scope', '=', 'tbai')],
                    order='date_end desc',
                    limit=1,
                )
            else:
                company.l10n_es_tbai_certificate_id = False

    @api.depends('country_id', 'l10n_es_tbai_test_env', 'l10n_es_tbai_tax_agency')
    def _compute_l10n_es_tbai_license_html(self):
        for company in self:
            license_dict = company._get_l10n_es_tbai_license_dict()
            if license_dict:
                license_dict.update({
                    'tr_nif': self.env._('Licence NIF'),
                    'tr_number': self.env._('Licence number'),
                    'tr_name': self.env._('Software name'),
                    'tr_version': self.env._('Software version')
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
<strong>{tr_no_license}</strong>''').format(tr_no_license=self.env._('TicketBAI is not configured'))

    def _get_l10n_es_tbai_license_dict(self):
        self.ensure_one()
        if self.l10n_es_tbai_is_enabled:
            if self.l10n_es_tbai_test_env:  # test env: each agency has its test license
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

    def _get_l10n_es_tbai_last_chained_document(self):
        """
        Returns the last tbai document posted to this company's chain.
        That tbai document may have been received by the govt or not (eg. in case of a timeout).
        Only upon confirmed reception/refusal of that tbai document can another one be posted.
        """
        domain = [
            ('chain_index', '!=', 0),
            ('company_id', '=', self.id)
        ]
        return self.env['l10n_es_edi_tbai.document'].search(domain, limit=1, order='chain_index desc')

    def _l10n_es_freelancer(self):
        self.ensure_one()
        return self.vat and re.fullmatch(r"(ES)?(\d{8}[A-Z]|[X-Z].*)", self.vat) or False
