from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner']

    ubl_cii_format = fields.Selection(selection_add=[('ubl_tr', "UBL TR 1.2")])
    l10n_tr_nilvera_customer_status = fields.Selection(
        selection=[
            ('not_checked', "Not Checked"),
            ('earchive', "E-Archive"),
            ('einvoice', "E-Invoice"),
        ],
        string="Nilvera Status",
        compute='_compute_nilvera_customer_status',
        store=True,
        copy=False,
        default='not_checked',
    )
    l10n_tr_nilvera_customer_alias_id = fields.Many2one(
        comodel_name='l10n_tr.nilvera.alias',
        string="Alias",
        domain="[('partner_id', '=', id)]",
        copy=False,
    )

    @api.depends('ubl_cii_format')
    def _compute_hide_peppol_fields(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_hide_peppol_fields()
        for partner in self:
            partner.hide_peppol_fields = bool(partner.ubl_cii_format == 'ubl_tr')

    @api.depends('country_code')
    def _compute_ubl_cii_format(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'TR':
                partner.ubl_cii_format = 'ubl_tr'

    @api.depends('vat', 'ubl_cii_format')
    def _compute_nilvera_customer_status(self):
        for partner in self:
            if partner.vat and partner.ubl_cii_format == 'ubl_tr':
                partner.check_nilvera_customer()
            else:
                partner.l10n_tr_nilvera_customer_alias_id = False

    def check_nilvera_customer(self):
        self.ensure_one()
        client = self.env.company._get_nilvera_client()
        response = client.request("GET", "/general/GlobalCompany/Check/TaxNumber/" + self.vat, handle_response=False)
        if response.status_code == 200:
            query_result = response.json()

            if not query_result:
                self.l10n_tr_nilvera_customer_status = 'earchive'
                self.l10n_tr_nilvera_customer_alias_id = False
            else:
                self.l10n_tr_nilvera_customer_status = 'einvoice'

                # We need to sync the data from the API with the records in database.
                aliases = [result.get('Name') for result in query_result]
                persisted_aliases = self.env['l10n_tr.nilvera.alias'].search([('partner_id', '=', self.id)])
                # Find aliases to add (in query result but not in database).
                aliases_to_add = set(aliases) - set(persisted_aliases.mapped('name'))
                # Find aliases to remove (in database but not in query result).
                aliases_to_remove = set(persisted_aliases.mapped('name')) - set(aliases)

                newly_persisted_aliases = self.env['l10n_tr.nilvera.alias'].create([{
                    'name': alias_name,
                    'partner_id': self.id,
                } for alias_name in aliases_to_add])
                persisted_aliases.filtered(lambda a: a.name in aliases_to_remove).unlink()

                # If no alias was previously selected, automatically select the first alias.
                remaining_aliases = newly_persisted_aliases | persisted_aliases.filtered(lambda a: a.name not in aliases_to_remove)
                if not self.l10n_tr_nilvera_customer_alias_id and remaining_aliases:
                    self.l10n_tr_nilvera_customer_alias_id = remaining_aliases[0]

    def _get_edi_builder(self):
        # EXTENDS 'account_edi_ubl_cii'
        if self.ubl_cii_format == 'ubl_tr':
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_edi_builder()
