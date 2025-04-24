from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL
from odoo.tools.misc import format_date

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils

INTEGRITY_HASH_BATCH_SIZE = 1000


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_pt_sale_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_sale.action_l10n_pt_sale_report_hash_integrity').report_action(self.id)

    def _l10n_pt_sale_check_hash_integrity(self):
        if self.account_fiscal_country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))

        self.env['sale.order']._l10n_pt_compute_missing_hashes(self)

        results = []

        at_series_lines = self.env['l10n_pt.at.series.line'].search([
            '|',
            '&',
            ('company_id', '=', self.id),
            ('company_exclusive_series', '=', True),
            '&',
            ('company_id', 'in', self.parent_ids.ids),
            ('company_exclusive_series', '=', False),
            ('type', 'in', ('sales_order', 'quotation')),
        ])

        for at_series_line in at_series_lines:
            query = self.env['sale.order'].sudo()._search(
                domain=[
                    ('l10n_pt_at_series_line_id', '=', at_series_line.id),
                    ('l10n_pt_sale_inalterable_hash', '!=', False),
                ],
                order="name",
            )

            first_order = self.env['sale.order']
            last_order = self.env['sale.order']
            corrupted_order = self.env['sale.order']

            self.env.execute_query(SQL("DECLARE hashed_orders CURSOR FOR %s", query.select()))
            while order_ids := self.env.execute_query(SQL("FETCH %s FROM hashed_orders", INTEGRITY_HASH_BATCH_SIZE)):
                self.env.invalidate_all()
                orders = self.env['sale.order'].browse([order_id[0] for order_id in order_ids])
                if not orders and not last_order:
                    results.append({
                        'series_at_code': at_series_line.at_code,
                        'status': 'no_data',
                        'msg_cover': _(
                            'No %(doc_type)s found for this AT series.',
                            doc_type='sales orders' if at_series_line.type == 'sales_order' else 'quotation',
                        ),
                    })
                    continue

                current_versioning_index = 0
                versioning_list = self._get_hash_versioning_list()  # defined in l10n_pt/res_company.py
                for order in orders:
                    if corrupted_order:
                        continue
                    if not self._verify_hashed_sales_order(order, last_order.l10n_pt_sale_inalterable_hash, versioning_list, current_versioning_index):
                        corrupted_order = order
                        continue
                    first_order = first_order or order
                    last_order = order

            self.env.execute_query(SQL("CLOSE hashed_orders"))
            if corrupted_order:
                results.append({
                    'series_document_identifier': at_series_line.document_identifier,
                    'series_at_code': at_series_line._get_at_code(),
                    'status': 'corrupted',
                    'msg_cover': _(
                        "Corrupted data on %(doc_type)s with id %(id)s (%(name)s).",
                        doc_type='sales order' if at_series_line.type == 'sales_order' else 'quotation',
                        id=corrupted_order.id,
                        name=corrupted_order.l10n_pt_document_number,
                    ),
                })
            elif first_order and last_order:
                results.append({
                    'series_document_identifier': at_series_line.document_identifier,
                    'series_at_code': at_series_line._get_at_code(),
                    'status': 'verified',
                    'msg_cover': _(
                        "%(doc_type)s are correctly hashed",
                        doc_type=_('Sales Orders') if at_series_line.type == 'sales_order' else _('Quotations'),
                    ),
                    'first_order': first_order,
                    'last_order': last_order,
                    'first_hash': first_order.l10n_pt_sale_inalterable_hash,
                    'first_name': first_order.name,
                    'first_document_number': first_order.l10n_pt_document_number,
                    'first_date': first_order.date_order,
                    'last_hash': last_order.l10n_pt_sale_inalterable_hash,
                    'last_name': last_order.name,
                    'last_document_number': last_order.l10n_pt_document_number,
                    'last_date': last_order.date_order,
                })

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.context_today(self)),
        }

    def _verify_hashed_sales_order(self, order, previous_hash, versioning_list, current_versioning_index):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        try:
            message = pt_hash_utils.get_message_to_hash(
                order.date_order,
                order.l10n_pt_hashed_on,
                order._get_l10n_pt_sale_document_number(),
                order.amount_total,
                previous_hash,
            )
            return pt_hash_utils.verify_integrity(
                message, order.l10n_pt_sale_inalterable_hash, versioning_list[current_versioning_index],
            )
        except AccessError as e:
            raise UserError(
                _("This company has AT Series shared across branches, and other companies also have hashed documents under this series. "
                  "To generate the report, please also select %s in the company selector.", e.context['suggested_company']['display_name']))
