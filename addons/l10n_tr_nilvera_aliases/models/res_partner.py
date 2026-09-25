import logging
import urllib.parse
from collections import Counter, defaultdict

from odoo import _, api, fields, models
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_tr_nilvera_customer_alias_id = fields.Many2one(
        domain="[('partner_id', '=', id), ('global_user_type', '=', 'Invoice')]",
    )
    l10n_tr_nilvera_edispatch_alias_id = fields.Many2one(
        domain="[('partner_id', '=', id), ('global_user_type', '=', 'DespatchAdvice')]",
    )

    @api.depends('l10n_tr_nilvera_customer_alias_ids.global_user_type', 'l10n_tr_nilvera_customer_status')
    def _compute_nilvera_customer_alias_id(self):
        for record in self:
            if (
                record.l10n_tr_nilvera_customer_status == 'einvoice'
                and (
                    not record.l10n_tr_nilvera_customer_alias_id
                    or record.l10n_tr_nilvera_customer_alias_id.global_user_type != 'Invoice'
                )
            ):
                record.l10n_tr_nilvera_customer_alias_id = record.l10n_tr_nilvera_customer_alias_ids.filtered(
                    lambda alias: alias.global_user_type == 'Invoice'
                )[:1]
            elif record.l10n_tr_nilvera_customer_status == 'earchive':
                record.l10n_tr_nilvera_customer_alias_id = False

    @api.depends('l10n_tr_nilvera_customer_alias_ids.global_user_type', 'l10n_tr_nilvera_customer_status')
    def _compute_l10n_tr_nilvera_edispatch_alias_id(self):
        for record in self:
            if (
                record.l10n_tr_nilvera_customer_status == 'einvoice'
                and (
                    not record.l10n_tr_nilvera_edispatch_alias_id
                    or record.l10n_tr_nilvera_edispatch_alias_id.global_user_type != 'DespatchAdvice'
                )
            ):
                record.l10n_tr_nilvera_edispatch_alias_id = record.l10n_tr_nilvera_customer_alias_ids.filtered(
                    lambda alias: alias.global_user_type == 'DespatchAdvice'
                )[:1]
            elif record.l10n_tr_nilvera_customer_status == 'earchive':
                record.l10n_tr_nilvera_edispatch_alias_id = False

    def _l10n_tr_nilvera_sync_customer_aliases(self, global_user_type):
        """ Synchronize aliases returned by Nilvera for a document type. """
        self.ensure_one()
        with _get_nilvera_client(self.env._, self.env.company) as client:
            response = client.request(
                "GET",
                f"/general/GlobalCompany/GetGlobalCustomerInfo/{urllib.parse.quote(self.vat)}",
                params={'globalUserType': global_user_type},
                handle_response=False,
            )
            if response.status_code != 200:
                return False

            query_result = response.json()
            aliases = {
                result.get('Name')
                for result in (query_result.get('Aliases') or [])
                if result.get('Name')
            }
            persisted_aliases = self.l10n_tr_nilvera_customer_alias_ids.filtered(
                lambda alias: alias.global_user_type == global_user_type
            )
            persisted_alias_names = set(persisted_aliases.mapped('name'))
            aliases_to_add = aliases - persisted_alias_names
            aliases_to_remove = persisted_alias_names - aliases

            if aliases_to_add:
                self.env['l10n_tr.nilvera.alias'].create([{
                    'name': alias_name,
                    'partner_id': self.id,
                    'global_user_type': global_user_type,
                } for alias_name in aliases_to_add])
            if aliases_to_remove:
                persisted_aliases.filtered(lambda alias: alias.name in aliases_to_remove).unlink()

            self.invalidate_recordset(['l10n_tr_nilvera_customer_alias_ids'])
            return True

    def _check_nilvera_customer(self):
        # OVERRIDE
        self.ensure_one()
        if not self.vat:
            return False

        with _get_nilvera_client(self.env._, self.env.company) as client:
            response = client.request(
                "GET",
                f"/general/GlobalCompany/Check/TaxNumber/{urllib.parse.quote(self.vat)}",
                handle_response=False,
            )
            if response.status_code != 200:
                return False

            query_result = response.json()
            if not query_result:
                self.l10n_tr_nilvera_customer_status = 'earchive'
            else:
                self.l10n_tr_nilvera_customer_status = 'einvoice'
                # Unlink any legacy unclassified aliases left from prior installations
                self.l10n_tr_nilvera_customer_alias_ids.filtered(lambda alias: not alias.global_user_type).unlink()
                if not (
                    self._l10n_tr_nilvera_sync_customer_aliases('Invoice')
                    and self._l10n_tr_nilvera_sync_customer_aliases('DespatchAdvice')
                ):
                    return False

            # As with the generic taxpayer check, retain results during a bulk verification.
            self.env.cr.commit()
            return True

    def _l10n_tr_nilvera_has_multiple_aliases(self):
        """ Check if the partner has multiple aliases for any single document type. """
        self.ensure_one()
        type_counts = Counter(self.l10n_tr_nilvera_customer_alias_ids.mapped('global_user_type'))
        return any(count > 1 for count in type_counts.values())

    def l10n_tr_check_nilvera_customer(self):
        # OVERRIDE
        results = defaultdict(lambda: self.env['res.partner'])
        retry_existing = self.env.context.get('retry_existing', False)
        for record in self.filtered(
            lambda p: p.vat and (retry_existing or p.l10n_tr_nilvera_customer_status == 'not_checked')
        ):
            if record._check_nilvera_customer():
                if record._l10n_tr_nilvera_has_multiple_aliases():
                    results['multi_alias'] |= record
                else:
                    results['success'] |= record
            else:
                results['failure'] |= record

        if results['failure']:
            self._send_user_notification('danger', self.env._('Nilvera verification failed. Please try again.'))
        if results['success']:
            self._send_user_notification('success', self.env._('Nilvera status verified successfully.'))
        if multi_alias := results['multi_alias']:
            self._send_user_notification(
                'warning',
                self.env._(
                    'Multiple alias entries were found for the following partners. '
                    'Please verify the correct one manually.'
                ),
                action_button={
                    'name': self.env._('View Partners'),
                    'action_name': self.env._('Partners in Error'),
                    'model': 'res.partner',
                    'res_ids': multi_alias.ids,
                },
            )
