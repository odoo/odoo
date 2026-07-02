# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from odoo import _, fields, models
from odoo.tools import float_compare, float_is_zero
import base64

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def validate_coupon_programs(self, point_changes, new_codes):
        """
        This is called upon validating the order in the pos.

        This will check the balance for any pre-existing coupon to make sure that the rewards are in fact all claimable.
        This will also check that any set code for coupons do not exist in the database.
        """
        point_changes = {int(k): v for k, v in point_changes.items()}
        coupon_ids_from_pos = set(point_changes.keys())
        coupons = self.env['loyalty.card'].browse(coupon_ids_from_pos).exists().filtered('program_id.active')
        coupon_difference = set(coupons.ids) ^ coupon_ids_from_pos
        if coupon_difference:
            return {
                'successful': False,
                'payload': {
                    'message': _('Some coupons are invalid. The applied coupons have been updated. Please check the order.'),
                    'removed_coupons': list(coupon_difference),
                }
            }
        for coupon in coupons:
            if float_compare(coupon.points, -point_changes[coupon.id], 2) == -1:
                return {
                    'successful': False,
                    'payload': {
                        'message': _('There are not enough points for the coupon: %s.', coupon.code),
                        'updated_points': {c.id: c.points for c in coupons}
                    }
                }
        # Check existing coupons
        coupons = self.env['loyalty.card'].search([('code', 'in', new_codes)])
        if coupons:
            return {
                'successful': False,
                'payload': {
                    'message': _('The following codes already exist in the database, perhaps they were already sold?\n%s',
                        ', '.join(coupons.mapped('code'))),
                }
            }
        return {
            'successful': True,
            'payload': {},
        }

    def add_loyalty_history_lines(self, coupon_data, coupon_updates):
        id_mapping = {item['old_id']: int(item['id']) for item in coupon_updates}
        history_lines_create_vals = []
        is_refund = self.amount_total < 0
        for coupon in coupon_data:
            card_id = id_mapping.get(int(coupon['card_id']), False) or int(coupon['card_id'])
            if not self.env['loyalty.card'].browse(card_id).exists():
                continue
            issued = coupon['won']
            cost = coupon['spent']
            if (issued or cost) and card_id > 0:
                description = _('Refund %s', self.display_name) if is_refund else _('Onsite %s', self.display_name)
                history_lines_create_vals.append({
                    'card_id': card_id,
                    'order_model': self._name,
                    'order_id': self.id,
                    'description': description,
                    'used': cost,
                    'issued': issued,
                })
        self.env['loyalty.history'].create(history_lines_create_vals)

    def confirm_coupon_programs(self, coupon_data):
        """
        This is called after the order is created.

        This will create all necessary coupons and link them to their line orders etc..

        It will also return the points of all concerned coupons to be updated in the cache.
        """
        get_partner_id = lambda partner_id: partner_id and self.env['res.partner'].browse(partner_id).exists() and partner_id or False
        # Keys are stringified when using rpc
        coupon_data = {int(k): v for k, v in coupon_data.items()}

        self._check_existing_loyalty_cards(coupon_data)
        self._remove_duplicate_coupon_data(coupon_data)
        # Map negative id to newly created ids.
        coupon_new_id_map = {k: k for k in coupon_data.keys() if k > 0}

        # Create the coupons that were awarded by the order.
        coupons_to_create = {k: v for k, v in coupon_data.items() if k < 0 and not v.get('giftCardId') and (v.get('points') or v.get('line_codes'))}
        for coupon in coupons_to_create.values():
            if "gift_code" in coupon:
                coupon["code"] = coupon.get("gift_code")
        coupon_create_vals = [{
            'program_id': p['program_id'],
            'partner_id': get_partner_id(p.get('partner_id', self.partner_id.id)),
            'code': p.get('code') or p.get('barcode') or self.env['loyalty.card']._generate_code(),
            'points': 0,
            'expiration_date': p.get('date_to', False),
            'source_pos_order_id': self.id,
            'expiration_date': p.get('expiration_date')
        } for p in coupons_to_create.values()]

        # Pos users don't have the create permission
        new_coupons = self.env['loyalty.card'].with_context(action_no_send_mail=True).sudo().create(coupon_create_vals)

        # We update the gift card that we sold when the gift_card_settings = 'scan_use'.
        gift_cards_to_update = [v for v in coupon_data.values() if v.get('giftCardId')]
        updated_gift_cards = self.env['loyalty.card']
        for coupon_vals in gift_cards_to_update:
            gift_card = self.env['loyalty.card'].browse(coupon_vals.get('giftCardId'))
            gift_card.write({
                'points': coupon_vals['points'],
                'source_pos_order_id': self.id,
                'partner_id': get_partner_id(coupon_vals.get('partner_id', False)),
            })
            updated_gift_cards |= gift_card

        # Map the newly created coupons
        for old_id, new_id in zip(coupons_to_create.keys(), new_coupons):
            coupon_new_id_map[new_id.id] = old_id

        # We need a sudo here because this can trigger `_compute_order_count` that require access to `sale.order.line`
        all_coupons = self.env['loyalty.card'].sudo().browse(coupon_new_id_map.keys()).exists()
        lines_per_reward_code = defaultdict(lambda: self.env['pos.order.line'])
        for line in self.lines:
            if not line.reward_identifier_code:
                continue
            lines_per_reward_code[line.reward_identifier_code] |= line
        for coupon in all_coupons:
            if coupon.id in coupon_new_id_map:
                # Coupon existed previously, update amount of points.
                coupon.points += coupon_data[coupon_new_id_map[coupon.id]]['points']
            for reward_code in coupon_data[coupon_new_id_map[coupon.id]].get('line_codes', []):
                lines_per_reward_code[reward_code].coupon_id = coupon
        # Send creation email
        new_coupons.with_context(action_no_send_mail=False)._send_creation_communication()
        # Reports per program
        report_per_program = {}
        coupon_per_report = defaultdict(list)
        # Important to include the updated gift cards so that it can be printed. Check coupon_report.
        for coupon in new_coupons | updated_gift_cards:
            if coupon.program_id not in report_per_program:
                report_per_program[coupon.program_id] = coupon.program_id.communication_plan_ids.\
                    filtered(lambda c: c.trigger == 'create').pos_report_print_id
            for report in report_per_program[coupon.program_id]:
                coupon_per_report[report.id].append(coupon.id)

        # Adding loyalty history lines
        loyalty_points = []
        for coupon_id, coupon_vals in coupon_data.items():
            if 'points_earned' in coupon_vals and 'points_spent' in coupon_vals:
                won = coupon_vals['points_earned']
                spent = coupon_vals['points_spent']
            else:
                won = coupon_vals['points'] if coupon_vals['points'] > 0 else 0
                spent = -coupon_vals['points'] if coupon_vals['points'] < 0 else 0
            loyalty_points.append({
                'order_id': self.id,
                'card_id': coupon_id,
                'spent': spent,
                'won': won,
            })
        coupon_updates = [
            {
                'id': coupon.id,
                'old_id': coupon_new_id_map[coupon.id],
            }
            for coupon in all_coupons
        ]
        self.add_loyalty_history_lines(loyalty_points, coupon_updates)

        return {
            'coupon_updates': [{
                'old_id': coupon_new_id_map[coupon.id],
                'id': coupon.id,
                'points': coupon.points,
                'code': coupon.code,
                'program_id': coupon.program_id.id,
                'partner_id': coupon.partner_id.id,
            } for coupon in all_coupons if coupon.program_id.is_nominative],
            'program_updates': [{
                'program_id': program.id,
                'usages': program.sudo().total_order_count,
            } for program in all_coupons.program_id],
            'new_coupon_info': [{
                'program_name': coupon.program_id.name,
                'expiration_date': coupon.expiration_date,
                'code': coupon.code,
            } for coupon in new_coupons if (
                coupon.program_id.applies_on == 'future'
                # Don't send the coupon code for the gift card and ewallet programs.
                # It should not be printed in the ticket.
                and coupon.program_id.sudo().program_type not in ['gift_card', 'ewallet']
            )],
            'coupon_report': coupon_per_report,
        }

    def _check_existing_loyalty_cards(self, coupon_data):
        coupon_key_to_modify = []
        for coupon_id, coupon_vals in coupon_data.items():
            partner_id = coupon_vals.get('partner_id', False)
            if partner_id:
                existing_coupon_for_program = self.env['loyalty.card'].search(
                    [('partner_id', '=', partner_id), ('program_type', 'in', ['loyalty', 'ewallet']), ('program_id', '=', coupon_vals['program_id'])])
                if existing_coupon_for_program:
                    coupon_vals['coupon_id'] = existing_coupon_for_program[0].id
                    coupon_key_to_modify.append([coupon_id, existing_coupon_for_program[0].id])
        for old_key, new_key in coupon_key_to_modify:
            coupon_data[new_key] = coupon_data.pop(old_key)

    def _remove_duplicate_coupon_data(self, coupon_data):
        # to prevent duplicates, it is necessary to check if the history line already exists
        items_to_remove = []
        for coupon_id, coupon_vals in coupon_data.items():
            existing_history = self.env['loyalty.history'].search_count([
                ('card_id.program_id', '=', coupon_vals['program_id']),
                ('order_model', '=', self._name),
                ('order_id', '=', self.id),
            ])
            if existing_history:
                items_to_remove.append(coupon_id)
        for item in items_to_remove:
            coupon_data.pop(item)

    def _get_fields_for_order_line(self):
        fields = super(PosOrder, self)._get_fields_for_order_line()
        fields.extend(['is_reward_line', 'reward_id', 'coupon_id', 'reward_identifier_code', 'points_cost'])
        return fields

    def action_pos_order_paid(self):
        """Override to reverse loyalty points when a refund order is paid."""
        res = super().action_pos_order_paid()
        self._reverse_loyalty_points_for_refund()
        return res

    def _reverse_loyalty_points_for_refund(self):
        """
        When a POS refund order is paid, find the original order's loyalty history
        and deduct the proportional points from the customer's loyalty card.

        Edge cases handled:
        - Partial refund: deducts proportional points based on refund/original ratio
        - Customer already spent points: deducts only up to current balance (no negative)
        - Customer has 0 points: skips deduction, still logs history
        - Expired card: skips deduction (card is no longer active)
        - Double-processing: idempotency guard via existing history check
        - No original loyalty history: skips silently
        """
        self.ensure_one()
        if self.amount_total >= 0:
            return
        original_order = self.refunded_order_id
        if not original_order:
            return

        original_history = self.env['loyalty.history'].search([
            ('order_model', '=', self._name),
            ('order_id', '=', original_order.id),
        ])
        if not original_history:
            return

        # Idempotency: skip if refund history already exists for this order
        already_processed = self.env['loyalty.history'].search_count([
            ('order_model', '=', self._name),
            ('order_id', '=', self.id),
        ])
        if already_processed:
            return

        # Partial refund ratio
        original_total = abs(original_order.amount_total)
        refund_total = abs(self.amount_total)
        ratio = min(refund_total / original_total, 1.0) if original_total else 1.0

        today = fields.Date.today()
        history_to_create = []

        for history_line in original_history:
            card = history_line.card_id

            # Edge case: card deleted or archived
            if not card.exists() or not card.active:
                continue

            # Edge case: expired card — skip entirely.
            # The card is already dead so there's nothing meaningful to deduct,
            # and we shouldn't touch the customer's other active cards.
            if card.expiration_date and card.expiration_date < today:
                continue

            # Skip gift_card / ewallet — handled separately
            if card.program_id.program_type in ('gift_card', 'ewallet'):
                continue

            points_to_reverse = round(history_line.issued * ratio, 2)
            if float_is_zero(points_to_reverse, precision_digits=2):
                continue

            # Always deduct the full amount even if it pushes the balance negative.
            # This prevents the fraud pattern: earn points → spend on reward → refund
            # the purchase → keep the reward for free.
            card.sudo().points -= points_to_reverse

            history_to_create.append({
                'card_id': card.id,
                'order_model': self._name,
                'order_id': self.id,
                'description': _('Refund %s', self.display_name),
                'used': points_to_reverse,
                'issued': 0,
            })

        if history_to_create:
            self.env['loyalty.history'].create(history_to_create)

    def _add_mail_attachment(self, name, ticket, basic_receipt):
        attachment = super()._add_mail_attachment(name, ticket, basic_receipt)
        gift_card_programs = self.config_id._get_program_ids().filtered(lambda p: p.program_type == 'gift_card' and
                                                                                  p.pos_report_print_id)
        if gift_card_programs:
            gift_cards = self.env['loyalty.card'].search([('source_pos_order_id', '=', self.id),
                                                          ('program_id', 'in', gift_card_programs.mapped('id'))])
            if gift_cards:
                for program in gift_card_programs:
                    filtered_gift_cards = gift_cards.filtered(lambda gc: gc.program_id == program)
                    if filtered_gift_cards:
                        action_report = program.pos_report_print_id
                        report = action_report._render_qweb_pdf(action_report.report_name, filtered_gift_cards.mapped('id'))
                        filename = name + '.pdf'
                        gift_card_pdf = self.env['ir.attachment'].create({
                            'name': filename,
                            'type': 'binary',
                            'datas': base64.b64encode(report[0]),
                            'store_fname': filename,
                            'res_model': 'pos.order',
                            'res_id': self.ids[0],
                            'mimetype': 'application/x-pdf'
                        })
                        attachment += [(4, gift_card_pdf.id)]

        return attachment
