from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools import SQL
from odoo.tools.misc import format_date

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils

INTEGRITY_HASH_BATCH_SIZE = 1000


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_pt_stock_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_stock.action_l10n_pt_stock_report_hash_integrity').report_action(self.id)

    def _l10n_pt_stock_check_hash_integrity(self):
        if self.account_fiscal_country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))

        self.env['stock.picking']._l10n_pt_compute_missing_hashes(self)

        results = []

        at_series_lines = self.env['l10n_pt.at.series.line'].search([
            '|',
            '&',
            ('company_id', '=', self.id),
            ('company_exclusive_series', '=', True),
            '&',
            ('company_id', 'in', self.parent_ids.ids),
            ('company_exclusive_series', '=', False),
            ('type', 'in', ('outgoing', 'internal', 'incoming')),
        ])

        for at_series_line in at_series_lines:
            query = self.env['stock.picking'].sudo()._search(
                domain=[
                    ('l10n_pt_at_series_id', '=', at_series_line.at_series_id.id),
                    ('picking_type_code', '=', at_series_line.type),
                    ('l10n_pt_stock_inalterable_hash', '!=', False),
                ],
                order="name",
            )

            first_picking = self.env['stock.picking']
            last_picking = self.env['stock.picking']
            corrupted_picking = self.env['stock.picking']

            self.env.execute_query(SQL("DECLARE hashed_pickings CURSOR FOR %s", query.select()))
            while picking_ids := self.env.execute_query(SQL("FETCH %s FROM hashed_pickings", INTEGRITY_HASH_BATCH_SIZE)):
                self.env.invalidate_all()
                pickings = self.env['stock.picking'].browse([picking_id[0] for picking_id in picking_ids])
                if not pickings and not last_picking:
                    results.append({
                        'series_at_code': at_series_line.at_code,
                        'status': 'no_data',
                        'msg_cover': _('No delivery orders found for this configuration.'),
                    })
                    continue

                current_versioning_index = 0
                versioning_list = self._get_hash_versioning_list()  # defined in l10n_pt/res_company.py
                for picking in pickings:
                    if corrupted_picking:
                        continue
                    if not self._verify_hashed_picking(picking, last_picking.l10n_pt_stock_inalterable_hash, versioning_list, current_versioning_index):
                        corrupted_picking = picking
                        continue
                    first_picking = first_picking or picking
                    last_picking = picking

            self.env.execute_query(SQL("CLOSE hashed_pickings"))
            if corrupted_picking:
                results.append({
                    'series_document_identifier': at_series_line.document_identifier,
                    'series_at_code': at_series_line._get_at_code(),
                    'status': 'corrupted',
                    'msg_cover': _(
                        "Corrupted data on delivery order with id %(id)s (%(name)s).",
                        id=corrupted_picking.id,
                        name=corrupted_picking.l10n_pt_document_number,
                    ),
                })
            elif first_picking and last_picking:
                results.append({
                    'series_document_identifier': at_series_line.document_identifier,
                    'series_at_code': at_series_line._get_at_code(),
                    'status': 'verified',
                    'msg_cover': _("Delivery orders are correctly hashed"),
                    'first_picking': first_picking,
                    'last_picking': last_picking,
                    'first_hash': first_picking.l10n_pt_stock_inalterable_hash,
                    'first_name': first_picking.name,
                    'first_document_number': first_picking.l10n_pt_document_number,
                    'first_date': first_picking.date_done,
                    'last_hash': last_picking.l10n_pt_stock_inalterable_hash,
                    'last_name': last_picking.name,
                    'last_document_number': last_picking.l10n_pt_document_number,
                    'last_date': last_picking.date_done,
                })

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.context_today(self)),
        }

    def _verify_hashed_picking(self, picking, previous_hash, versioning_list, current_versioning_index):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        try:
            message = pt_hash_utils.get_message_to_hash(
                picking.date_done, picking.l10n_pt_hashed_on, picking._get_l10n_pt_stock_document_number(), 0, previous_hash,
            )
            return pt_hash_utils.verify_integrity(
                message, picking.l10n_pt_stock_inalterable_hash, versioning_list[current_versioning_index],
            )
        except AccessError as e:
            raise UserError(
                _("This company has AT Series shared across branches, and other companies also have hashed documents under this series. "
                  "To generate the report, please also select %s in the company selector.", e.context['suggested_company']['display_name']))
