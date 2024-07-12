from odoo import fields, models, _, api
from odoo.exceptions import UserError
from odoo.tools import SQL
from odoo.tools.misc import format_date

from odoo.addons.l10n_pt.utils import hashing as pt_hash_utils

INTEGRITY_HASH_BATCH_SIZE = 1000


class ResCompany(models.Model):
    _inherit = "res.company"

    @api.model
    def _l10n_pt_stock_action_check_hash_integrity(self):
        return self.env.ref('l10n_pt_stock.action_l10n_pt_stock_report_hash_integrity').report_action(self.id)

    def _l10n_pt_stock_check_hash_integrity(self):
        if self.account_fiscal_country_id.code != 'PT':
            raise UserError(_('This feature is only available for Portuguese companies.'))

        self.env['stock.picking']._l10n_pt_stock_compute_missing_hashes(self.id)

        results = []

        picking_types = self.env['stock.picking.type'].search([
            ('company_id', '=', self.id),
            ('code', '=', 'outgoing'),
            ('l10n_pt_stock_at_series_id', '!=', False),
        ])

        for picking_type in picking_types:
            query = self.env['stock.picking'].sudo()._search(
                domain=[
                    ('picking_type_id', '=', picking_type.id),
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
                pickings = self.env['stock.picking'].browse(picking_id[0] for picking_id in picking_ids)
                if not pickings and not last_picking:
                    results.append({
                        'config_at_code': picking_type.l10n_pt_stock_at_series_id.code,
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
                    'picking_type_prefix': picking_type.l10n_pt_stock_at_series_id.prefix,
                    'picking_type_at_code': picking_type.l10n_pt_stock_at_series_id._get_at_code(),
                    'status': 'corrupted',
                    'msg_cover': _(
                        "Corrupted data on delivery order with id %(id)s (%(name)s).",
                        id=corrupted_picking.id,
                        name=corrupted_picking.name,
                    ),
                })
            else:
                results.append({
                    'picking_type_prefix': picking_type.l10n_pt_stock_at_series_id.prefix,
                    'picking_type_at_code': picking_type.l10n_pt_stock_at_series_id._get_at_code(),
                    'status': 'verified',
                    'msg_cover': _("Delivery orders are correctly hashed"),
                    'first_picking': first_picking,
                    'last_picking': last_picking,
                    'first_hash': first_picking.l10n_pt_stock_inalterable_hash,
                    'first_name': first_picking.name,
                    'first_date': first_picking.date_done,
                    'last_hash': last_picking.l10n_pt_stock_inalterable_hash,
                    'last_name': last_picking.name,
                    'last_date': last_picking.date_done,
                })

        return {
            'results': results,
            'printing_date': format_date(self.env, fields.Date.context_today(self)),
        }

    def _verify_hashed_picking(self, picking, previous_hash, versioning_list, current_versioning_index):
        previous_hash = previous_hash.split("$")[2] if previous_hash else ""
        message = pt_hash_utils.get_message_to_hash(picking.date_done, picking.l10n_pt_hashed_on, 0, picking._get_l10n_pt_stock_document_number(), previous_hash)
        return pt_hash_utils.verify_integrity(message, picking.l10n_pt_stock_inalterable_hash, versioning_list[current_versioning_index])
