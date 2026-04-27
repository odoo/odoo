# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict
import itertools
from psycopg2.errors import LockNotAvailable

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import groupby
from odoo.tools.float_utils import json_float_round


class StockMove(models.Model):
    _inherit = 'stock.move'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    l10n_ke_oscu_flow_type_code = fields.Selection(
        selection=[
            ('01', "Import Incoming"),
            ('02', "Purchase Incoming"),
            ('03', "Return Incoming"),
            ('04', "Stock Movement Incoming"),
            ('05', "Processing Incoming"),
            ('06', "Adjustment Incoming"),
            ('11', "Sale Outgoing"),
            ('12', "Return Outgoing"),
            ('13', "Stock Movement Outgoing"),
            ('14', "Processing Outgoing"),
            ('15', "Discarding Outgoing"),
            ('16', "Adjustment Outgoing"),
        ],
        compute='_compute_l10n_ke_oscu_flow_type_code',
        string="eTIMS Category",
        store=True, readonly=False, copy=False,
    )
    l10n_ke_oscu_sar_number = fields.Integer(
        string="Store and Release Number",
        copy=False,
        help="Number used by the KRA to identify stock movements",
    )
    l10n_ke_oscu_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="eTIMS Stock IO content",
        copy=False,
        help="JSON file sent to eTIMS for Stock IO",
        ondelete='set null',
        groups='base.group_system',
    )

    # === Computes === #

    @api.depends('location_id.usage', 'location_dest_id.usage', 'partner_id')
    def _compute_l10n_ke_oscu_flow_type_code(self):
        flow_mappings = {
            # Partner type, location_id.usage, location_dest_id.usage
            # ruff: noqa: E241
            ('external', 'supplier',   'internal'):   '02',  # Purchase Incoming
            (False,      'customer',   'internal'):   '03',  # Return Incoming
            ('branch',   'supplier',   'internal'):   '04',  # Stock Move Incoming
            (False,      'production', 'internal'):   '05',  # Processing Incoming
            (False,      'inventory',  'internal'):   '06',  # Adjustment Incoming
            (False,      'supplier',   'internal'):   '06',
            ('external', 'internal',   'customer'):   '11',  # Sale Outgoing
            (False,      'internal',   'supplier'):   '12',  # Return Outgoing
            ('branch',   'internal',   'customer'):   '13',  # Stock Move Outgoing
            (False,      'internal',   'production'): '14',  # Processing Outgoing
            (False,      'internal',   'customer'):   '16',  # Adjustment Outgoing
            (False,      'internal',   'inventory'):  '16',  # Adjustment Outgoing
        }
        ke_moves = self.filtered(lambda m: m.company_id.country_id.code == "KE")
        (self - ke_moves).l10n_ke_oscu_flow_type_code = False

        for move in ke_moves:
            if move.scrapped:
                move.l10n_ke_oscu_flow_type_code = '15'      # Discarding Outgoing
                continue

            partner_type = 'internal'
            if partner := move.picking_id.partner_id:
                company = self.env['res.company'].search([('partner_id', '=', partner.id)], limit=1)
                partner_type = 'branch' if company and company.account_fiscal_country_id.code == 'KE' else 'external'

            code = flow_mappings.get(
                (partner_type, move.location_id.usage, move.location_dest_id.usage)
            ) or flow_mappings.get((False, move.location_id.usage, move.location_dest_id.usage))
            if code == '02' and move.picking_id.partner_id.country_id.code not in ['KE', False]:
                code = '01'
            move.l10n_ke_oscu_flow_type_code = code

    @api.ondelete(at_uninstall=False)
    def _unlink_only_if_unsent(self):
        if self.filtered(lambda m: m.sudo().l10n_ke_oscu_attachment_id):
            raise UserError(_('You cannot delete a stock move once it has been sent to eTIMS!'))

    # === Overrides === #

    def _action_done(self, cancel_backorder=False):
        # EXTENDS 'stock'
        res = super()._action_done(cancel_backorder=cancel_backorder)
        if self.filtered(lambda m: m.l10n_ke_oscu_flow_type_code):
            self.env.ref('l10n_ke_edi_oscu_stock.ir_cron_send_stock_moves')._trigger()
        return res

    # === Sending to KRA: Stock IO === #

    def _calculate_unit_cost(self):
        """ For stockable products we can easily use the stock valuation layers to calculate the unit price"""
        self.ensure_one()
        unit_price = 0
        quantity_product_uom = self.product_uom._compute_quantity(self.quantity, self.product_id.uom_id)
        for layer in self.stock_valuation_layer_ids:
            unit_price += layer.unit_cost * (quantity_product_uom / layer.quantity)
        return unit_price

    def _l10n_ke_oscu_save_stock_io_content(self):
        """ Send a recordset of stock moves to eTIMS.
            All records should have the same partner_id, flow type code and date.
        """
        first_move = self[0]
        customer_info = {
            'custTin':   first_move.partner_id.vat or None,   # Customer TIN
            'custNm':    first_move.partner_id.name or None,  # Customer Name
            'custBhfId': first_move.partner_id.l10n_ke_branch_code or None,  # Customer Branch ID
        }

        lines_vals = []
        for index, move in enumerate(self):
            product = move.product_id  # for ease of use
            taxes = product.taxes_id.filtered(lambda tax: tax.l10n_ke_tax_type_id)
            tax_rate = (taxes[0].amount / 100) if taxes else 0
            quantity_product_uom = move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id)

            # but get from product for now
            price = abs(move._calculate_unit_cost()) * (move.quantity / quantity_product_uom)
            price = price or move.product_id.standard_price  # Suppose the user forgot to set it
            base_amount = quantity_product_uom * price

            lines_vals.append({
                'itemSeq':   index + 1,
                'itemCd':    product.l10n_ke_item_code,                    # Item code (if it's there)
                'itemClsCd': product.unspsc_code_id.code,                  # UNSPSC Code
                'itemNm':    product.name,                                 # Product name
                'bcd':       product.barcode or '',                        # Barcode
                'pkgUnitCd': product.l10n_ke_packaging_unit_id.code,       # Packaging unit code
                'pkg':       json_float_round(quantity_product_uom / product.l10n_ke_packaging_quantity, 2),  # Packaging quantity
                'qtyUnitCd': move.product_uom.l10n_ke_quantity_unit_id.code,  # UoM (but as defined by Kenya)
                'qty':       json_float_round(move.quantity, 2),           # Quantity
                'prc':       json_float_round(price, 2),                   # Unit price cost
                'splyAmt':   json_float_round(base_amount, 2),             # Cost of items
                'totDcAmt':  0,                                            # Total discount amount
                'taxblAmt':  json_float_round(base_amount, 2),             # Taxable amount
                'taxTyCd':   product._l10n_ke_get_tax_type().code,         # Tax type code
                'taxAmt':    json_float_round(base_amount * tax_rate, 2),  # Tax amount
                'totAmt':    json_float_round(base_amount * (1 + tax_rate), 2)  # Total amount
            })

        content = {
            **customer_info,
            'regTyCd':     'M',                                     # Registration type code (if this becomes automatic, then A)
            'sarTyCd':     first_move.l10n_ke_oscu_flow_type_code,  # Stored and released type code
            'ocrnDt':      first_move.date.strftime('%Y%m%d'),      # Occurred date
            **self.env.company._l10n_ke_get_user_dict(first_move.create_uid, first_move.write_uid),
            'totItemCnt':  len(self),
            'totTaxblAmt': json_float_round(sum(float(line['taxblAmt']) for line in lines_vals), 2),
            'totTaxAmt':   json_float_round(sum(float(line['taxAmt']) for line in lines_vals), 2),
            'totAmt':      json_float_round(sum(float(line['totAmt']) for line in lines_vals), 2),
            'itemList':    lines_vals,
        }
        return content

    def _l10n_ke_oscu_save_stock_io(self):
        content = {
            **self._l10n_ke_oscu_save_stock_io_content(),
            'orgSarNo': self[0].picking_id.backorder_id and self[0].picking_id.backorder_id.move_ids[0].l10n_ke_oscu_sar_number or 0,
        }
        try:
            content['sarNo'] = self.company_id._l10n_ke_get_sar_sequence().next_by_id()
        except LockNotAvailable:
            raise UserError(_("Another user is already sending this picking.")) from None

        self.l10n_ke_oscu_sar_number = content['sarNo']

        error, _dummy, _dummy = self.company_id._l10n_ke_call_etims('insertStockIO', content)

        if error:
            # Instead of rolling back entirely, we just unassign the number and unincrement the sequence
            self.l10n_ke_oscu_sar_number = False
            self.company_id._l10n_ke_get_sar_sequence().number_next -= 1

        return error, content

    @api.model
    def _l10n_ke_oscu_process_moves(self):
        """ Send the stock moves in `self` to eTIMS:
            - register the product if needed
            - send the stock IOs for the moves batched by picking, date, and flow type code
            - send the stock master for all products for which at least one stock IO was successfully sent.
        """
        if not self:
            return
        # Step 1: Register products
        products_to_register = self.product_id.filtered(lambda p: not p.l10n_ke_item_code)

        products_data = defaultdict(dict)
        for product in products_to_register:
            error, content = product._l10n_ke_oscu_save_item()
            products_data[product]['registration_content'] = content
            products_data[product]['registration_error'] = error

        if self.env['account.move.send']._can_commit():
            self.env.cr.commit()

        # Step 2: Send Stock IO for moves.
        # Moves with a picking should grouped by picking ID. Moves without should be grouped by flow type code and date.
        # Only send moves for products that were successfully registered.
        moves_to_send = self.filtered(lambda m: m.product_id.l10n_ke_item_code)
        move_send_batches = {
            move_batch_key: self.env['stock.move'].union(*moves).with_prefetch(moves_to_send.ids)
            for move_batch_key, moves in groupby(moves_to_send, lambda m: (m.picking_id, m.l10n_ke_oscu_flow_type_code, m.date))
        }
        move_batches_data = defaultdict(dict)
        products_to_send_stock_master = self.env['product.product']
        for move_batch_key, moves in move_send_batches.items():
            error, content = moves._l10n_ke_oscu_save_stock_io()
            move_batches_data[move_batch_key]['content'] = content
            move_batches_data[move_batch_key]['error'] = error
            if not error:
                products_to_send_stock_master |= moves.product_id
                if self.env['account.move.send']._can_commit():
                    self.env.cr.commit()

        # Step 3: Send Stock Master for all products where at least one Stock IO succeeded.
        for product in products_to_send_stock_master:
            error, content = product._l10n_ke_oscu_save_stock_master()
            products_data[product]['stock_master_content'] = content
            products_data[product]['stock_master_error'] = error
        if self.env['account.move.send']._can_commit():
            self.env.cr.commit()

        # Step 4: Update picking error message
        is_error = False
        for picking in self.picking_id:
            move_batch_keys = {(m.picking_id, m.l10n_ke_oscu_flow_type_code, m.date) for m in picking.move_ids}
            errors = list(itertools.chain(
       (products_data[product].get('registration_error') for product in picking.move_ids.product_id),
                (move_batches_data[move_batch_key].get('error') for move_batch_key in move_batch_keys),
                (products_data[product].get('stock_master_error') for product in picking.move_ids.product_id),
            ))
            unique_errors = list({f"{e['code']} {e['message']}" for e in errors if e})  # Don't show duplicate errors
            if unique_errors:
                is_error = True
            picking.l10n_ke_error_msg = {
                f'message_{i}': {
                    'message': error_msg,
                }
                for i, error_msg in enumerate(unique_errors)
            }

        # Step 5: Create attachments on stock.move, one for each batch that was *successfully* sent.
        for move_batch_key, moves in move_send_batches.items():
            if not move_batches_data[move_batch_key]['error']:
                contents = list(itertools.chain(
                    (
                        products_data[product]['register_content']
                        for product in moves.product_id
                        if 'register_content' in products_data[product]
                    ),
                    (
                        move_batches_data[move_batch_key]['content']
                    ),
                    (
                        products_data[product]['stock_master_content']
                        for product in moves.product_id
                        if 'stock_master_content' in products_data[product]
                    )
                ))

                picking, flow_type_code, date = move_batch_key
                if picking:
                    filename_prefix = f"KRA_stock_{picking.name.replace('/', '_')}"
                else:
                    filename_prefix = f"KRA_stock_{flow_type_code}_{date}"

                filename = f'{filename_prefix}.json'
                i = 1
                while self.env['ir.attachment'].search_count([('name', '=', filename)], limit=1):
                    filename = f'{filename_prefix}_{i}.json'
                    i += 1

                attachment = self.env['ir.attachment'].create({
                    'name': filename,
                    'raw': json.dumps(contents, indent=4),
                    'res_model': picking.id and 'stock.picking',
                    'res_id': picking.id,
                })
                moves.sudo().write({
                    'l10n_ke_oscu_attachment_id': attachment.id,
                })

        return is_error

    @api.model
    def _cron_l10n_ke_oscu_process_moves(self):
        companies = self.env.companies.filtered(lambda c: c.l10n_ke_oscu_is_active)

        for company in companies:
            # Determine stock moves to send
            moves_need_reporting_domain = [
                ('product_id.is_storable', '=', True),
                ('state', '=', 'done'),
                ('l10n_ke_oscu_flow_type_code', '!=', False),
                ('l10n_ke_oscu_sar_number', '=', False),
                ('company_id', '=', company.id),
            ]

            # This param is set when l10n_ke_edi_oscu_stock is installed, and ensures that old moves are not sent.
            if from_date := self.env['ir.config_parameter'].sudo().get_param('l10n_ke.start_stock_date'):
                moves_need_reporting_domain += [('date', '>=', from_date)]

            # We set the env company here because it is needed for the stock master to correctly compute product quantities.
            moves_need_reporting = self.with_context(allowed_company_ids=company.ids).search(moves_need_reporting_domain, order='date,id')

            # Don't send moves linked to a picking if the corresponding invoice wasn't yet sent (KRA requirement)
            # or if there is missing information on the product / UoM.
            moves_need_reporting = moves_need_reporting.filtered(
                lambda m: (
                    not m.picking_id.l10n_ke_validation_msg
                    if m.picking_id
                    else (
                        not m.product_id._l10n_ke_get_validation_messages()
                        and not m.product_uom._l10n_ke_get_validation_messages()
                    )
                )
            )
            moves_need_reporting._l10n_ke_oscu_process_moves()

    def action_l10n_ke_oscu_process_moves(self):
        if any(not p.is_storable for p in self.product_id):
            raise UserError(_("Only stockable products may be sent."))
        if any(m.l10n_ke_oscu_sar_number for m in self):
            raise UserError(_("This stock move has already been sent."))
        if any(p._l10n_ke_get_validation_messages() for p in self.product_id):
            raise UserError(_("Information is missing on the product."))
        if any(uom._l10n_ke_get_validation_messages() for uom in self.product_uom):
            raise UserError(_("Information is missing on the unit of measure."))

        is_error = self._l10n_ke_oscu_process_moves()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if not is_error else 'danger',
                'sticky': False,
                'message': (
                    _("Stock IO and stock master successfully reported")
                    if not is_error
                    else _("Some errors occurred while reporting stock IO and stock master, see pickings for error messages.")
                ),
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
