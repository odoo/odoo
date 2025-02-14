import logging
import urllib.parse

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client


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
        compute='_compute_nilvera_customer_status_and_alias_id',
        store=True,
        copy=False,
        default='not_checked',
    )
    l10n_tr_nilvera_customer_alias_id = fields.Many2one(
        comodel_name='l10n_tr.nilvera.alias',
        string="Alias",
        compute='_compute_nilvera_customer_status_and_alias_id',
        domain="[('partner_id', '=', id)]",
        copy=False,
        store=True,
        readonly=False,
    )

    # This field is only used technically for optimisation purposes. It's needed for check_nilvera_customer.
    l10n_tr_nilvera_customer_alias_ids = fields.One2many(
        comodel_name='l10n_tr.nilvera.alias',
        inverse_name="partner_id",
    )

    @api.depends('ubl_cii_format')
    def _compute_hide_peppol_fields(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_hide_peppol_fields()
        for partner in self:
            partner.hide_peppol_fields = partner.ubl_cii_format == 'ubl_tr'

    @api.depends('country_code')
    def _compute_ubl_cii_format(self):
        # EXTENDS 'account_edi_ubl_cii'
        super()._compute_ubl_cii_format()
        for partner in self:
            if partner.country_code == 'TR':
                partner.ubl_cii_format = 'ubl_tr'

    @api.depends('vat', 'ubl_cii_format')
    def _compute_nilvera_customer_status_and_alias_id(self):
        for partner in self:
            if partner.vat and partner.ubl_cii_format == 'ubl_tr':
                try:
                    partner.check_nilvera_customer()
                except UserError:
                    # In case of an internet connection issue, exit silently.
                    continue
            else:
                # Reset the alias if no VAT or UBL format changed.
                partner.l10n_tr_nilvera_customer_status = 'not_checked'
                partner.l10n_tr_nilvera_customer_alias_id = False

    def check_nilvera_customer(self):
        self.ensure_one()
        if not self.vat:
            return

        with _get_nilvera_client(self.env.company) as client:
            response = client.request("GET", "/general/GlobalCompany/Check/TaxNumber/" + urllib.parse.quote(self.vat), handle_response=False)
            if response.status_code == 200:
                query_result = response.json()

                if not query_result:
                    self.l10n_tr_nilvera_customer_status = 'earchive'
                    self.l10n_tr_nilvera_customer_alias_id = False
                else:
                    self.l10n_tr_nilvera_customer_status = 'einvoice'

                    # We need to sync the data from the API with the records in database.
                    aliases = {result.get('Name') for result in query_result}
                    persisted_aliases = self.l10n_tr_nilvera_customer_alias_ids
                    # Find aliases to add (in query result but not in database).
                    aliases_to_add = aliases - set(persisted_aliases.mapped('name'))
                    # Find aliases to remove (in database but not in query result).
                    aliases_to_remove = set(persisted_aliases.mapped('name')) - aliases

                    newly_persisted_aliases = self.env['l10n_tr.nilvera.alias'].create([{
                        'name': alias_name,
                        'partner_id': self.id,
                    } for alias_name in aliases_to_add])
                    to_keep = persisted_aliases.filtered(lambda a: a.name not in aliases_to_remove)
                    (persisted_aliases - to_keep).unlink()

                    # If no alias was previously selected, automatically select the first alias.
                    remaining_aliases = newly_persisted_aliases | to_keep
                    if not self.l10n_tr_nilvera_customer_alias_id and remaining_aliases:
                        self.l10n_tr_nilvera_customer_alias_id = remaining_aliases[0]

    def _get_edi_builder(self):
        # EXTENDS 'account_edi_ubl_cii'
        if self.ubl_cii_format == 'ubl_tr':
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_edi_builder()
