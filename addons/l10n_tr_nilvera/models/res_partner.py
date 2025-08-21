import logging
import urllib.parse

from collections import defaultdict

from odoo import _, api, fields, models
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner']

    invoice_edi_format = fields.Selection(selection_add=[('ubl_tr', "Türkiye (UBL TR 1.2)")])
    l10n_tr_nilvera_customer_status = fields.Selection(
        selection=[
            ('not_checked', "Not Verified"),
            ('earchive', "E-Archive"),
            ('einvoice', "E-Invoice"),
        ],
        string="Nilvera Status",
        copy=False,
        default='not_checked',
        readonly=True,
        tracking=True,
    )
    l10n_tr_nilvera_customer_alias_id = fields.Many2one(
        comodel_name='l10n_tr.nilvera.alias',
        string="Alias",
        compute='_compute_nilvera_customer_alias_id',
        domain="[('partner_id', '=', id)]",
        copy=False,
        store=True,
        readonly=False,
    )

    # This field is only used technically for optimisation purposes. It's needed for _check_nilvera_customer.
    l10n_tr_nilvera_customer_alias_ids = fields.One2many(
        comodel_name='l10n_tr.nilvera.alias',
        inverse_name="partner_id",
    )

    @api.depends('l10n_tr_nilvera_customer_alias_ids')
    def _compute_nilvera_customer_alias_id(self):
        for record in self:
            record.l10n_tr_nilvera_customer_alias_id = record.l10n_tr_nilvera_customer_alias_ids[:1]

    def _send_user_notification(self, type, message, action_button=None):
        self.env.user._bus_send(
            'account_notification' if action_button else 'simple_notification',
            {
                'type': type,
                'message': message,
                'action_button': action_button,
            }
        )

    def l10n_tr_check_nilvera_customer(self):
        results = defaultdict(lambda: self.env['res.partner'])
        for record in self:
            if not record.vat:
                return

            if record._check_nilvera_customer():
                if len(record.l10n_tr_nilvera_customer_alias_ids) > 1:
                    results['multi_alias'] |= record
                else:
                    results['success'] |= record
            else:
                results['failure'] |= record

        if results['failure']:
            self._send_user_notification('danger', _('Nilvera verification failed. Please try again.'))
        if results['success']:
            self._send_user_notification('success', _('Nilvera status verified successfully.'))
        if multi_alias := results['multi_alias']:
            self._send_user_notification(
                'warning',
                _('Multiple alias entries were found for the following partners. Please verify the correct one manually.'),
                action_button={
                    'name': _('View Partners'),
                    'action_name': _('Partners in Error'),
                    'model': 'res.partner',
                    'res_ids': multi_alias.ids,
                },
            )

    def _check_nilvera_customer(self):
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
                return True
            else:
                return False

    def _get_suggested_invoice_edi_format(self):
        # EXTENDS 'account'
        res = super()._get_suggested_invoice_edi_format()
        if self.country_code == 'TR':
            return 'ubl_tr'
        else:
            return res

    def _get_edi_builder(self, invoice_edi_format):
        # EXTENDS 'account_edi_ubl_cii'
        if invoice_edi_format == 'ubl_tr':
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_edi_builder(invoice_edi_format)

    def _get_ubl_cii_formats_info(self):
        # EXTENDS 'account_edi_ubl_cii'
        formats_info = super()._get_ubl_cii_formats_info()
        formats_info['ubl_tr'] = {'countries': ['TR']}
        return formats_info
