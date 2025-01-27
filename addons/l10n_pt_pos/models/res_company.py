from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.misc import format_date

from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils

INTEGRITY_HASH_BATCH_SIZE = 1000


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_pt_pos_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_pos.action_l10n_pt_pos_report_hash_integrity').report_action(self.id)

    def _l10n_pt_pos_check_hash_integrity(self):
        if self.account_fiscal_country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))

        results = []

        pos_configs = self.env['pos.config'].search([
            ('company_id', '=', self.id),
            ('l10n_pt_pos_at_series_id', '!=', False),
        ])

        for pos_config in pos_configs:
            self.env['pos.order'].l10n_pt_pos_compute_missing_hashes(pos_config.company_id.id, pos_config.id)
            query = self.env['pos.order'].sudo()._search(
                domain=[
                    ('config_id', '=', pos_config.id),
                    ('l10n_pt_pos_inalterable_hash', '!=', False),
                ],
                order="name",
            )
            first_order = self.env['pos.order']
            last_order = self.env['pos.order']
            corrupted_order = self.env['pos.order']
            self.env.execute_query(SQL("DECLARE hashed_orders CURSOR FOR %s", query.select()))
            while order_ids := self.env.execute_query(SQL("FETCH %s FROM hashed_orders", INTEGRITY_HASH_BATCH_SIZE)):
                self.env.invalidate_all()
                orders = self.env['pos.order'].browse(order_id[0] for order_id in order_ids)
                if not orders and not last_order:
                    results.append({
                        'config_at_code': pos_config.l10n_pt_pos_at_series_id.code,
                        'status': 'no_data',
                        'msg_cover': _('No POS orders found for this configuration.'),
                    })
                    continue

                current_versioning_index = 0
                versioning_list = self._get_hash_versioning_list()  # defined in l10n_pt/res_company.py
                for order in orders:
                    if corrupted_order:
                        continue
                    if not self._verify_hashed_order(order, last_order.l10n_pt_pos_inalterable_hash, versioning_list, current_versioning_index):
                        corrupted_order = order
                        continue
                    first_order = first_order or order
                    last_order = order

            self.env.execute_query(SQL("CLOSE hashed_orders"))
            if corrupted_order:
                results.append({
                    'config_prefix': pos_config.l10n_pt_pos_at_series_id.prefix,
                    'config_at_code': pos_config.l10n_pt_pos_at_series_id._get_at_code(),
                    'status': 'corrupted',
                    'msg_cover': _(
                        "Corrupted data on POS order with id %(id)s (%(name)s).",
                        id=corrupted_order.id,
                        name=corrupted_order.name,
                    ),
                })
            else:
                results.append({
                    'config_prefix': pos_config.l10n_pt_pos_at_series_id.prefix,
                    'config_at_code': pos_config.l10n_pt_pos_at_series_id._get_at_code(),
                    'status': 'verified',
                    'msg_cover': _("Orders are correctly hashed"),
                    'first_order': first_order,
                    'last_order': last_order,
                    'first_hash': first_order.l10n_pt_pos_inalterable_hash,
                    'first_name': first_order.name,
                    'first_date': first_order.date_order,
                    'last_hash': last_order.l10n_pt_pos_inalterable_hash,
                    'last_name': last_order.name,
                    'last_date': last_order.date_order,
                })

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.context_today(self)),
        }

    def _verify_hashed_order(self, order, previous_hash, versioning_list, current_versioning_index):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        message = pt_hash_utils.get_message_to_hash(order.date_order, order.l10n_pt_hashed_on, order.amount_total, order._get_l10n_pt_pos_document_number(), previous_hash)
        return pt_hash_utils.verify_integrity(message, order.l10n_pt_pos_inalterable_hash, versioning_list[current_versioning_index])
