# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare
from odoo.tools.image import image_data_uri


class PosOrder(models.Model):
    _inherit = 'pos.order'

    applied_codes = fields.Json(default=list, copy=False)

    active_rewards = fields.Json(default=list, copy=False)
    active_payment_programs = fields.Json(default=list, copy=False)
    disabled_program_ids = fields.Json(default=list, copy=False)

    def _process_saved_order(self, draft):
        """
        Override to update loyalty points and generate history lines
        """
        res = super()._process_saved_order(draft)
        if not draft and self.state != 'cancel':
            self._process_loyalty()

        return res

    def read_pos_data(self, data, config):
        """Return the loyalty cards touched by these orders alongside the order data.

        ``_process_loyalty`` credits/debits cards server-side after the order is saved, but
        the base sync response carries no ``loyalty.card`` records. Without this, a card sold
        or credited on the order keeps its stale in-memory balance (e.g. a gift card sold and
        then redeemed in the same session would read a 0 balance). Sending the cards back lets
        the client refresh their points via ``loadConnectedData``.
        """
        result = super().read_pos_data(data, config)
        if config:
            history = self.env['loyalty.history'].search([
                ('order_model', '=', 'pos.order'),
                ('order_id', 'in', self.ids),
            ])
            cards = self.lines.card_id | history.card_id
            result['loyalty.card'] = self.env['loyalty.card']._load_pos_data_read(cards, config)

            new_coupon_cards = cards.filtered(lambda c: c._is_new_receipt_coupon(self))
            barcode_by_card = {
                card.id: image_data_uri(
                    self.env['ir.actions.report'].barcode('Code128', card.code, quiet=False)
                )
                for card in new_coupon_cards
            }
            report_by_card = {}
            for line in self.lines:
                card = line.card_id
                if (card and card.source_pos_order_id in self
                        and card.program_id.program_type == 'gift_card'
                        and not (line.gift_card_vals or {}).get('code')
                        and card.program_id.pos_report_print_id):
                    report_by_card[card.id] = card.program_id.pos_report_print_id.id

            for card_data in result['loyalty.card']:
                if card_data['id'] in barcode_by_card:
                    card_data['_barcode_base64'] = barcode_by_card[card_data['id']]
                if card_data['id'] in report_by_card:
                    card_data['_pos_report_print_id'] = report_by_card[card_data['id']]

            programs = self.lines.filtered('is_reward_line').reward_id.program_id
            if programs:
                programs.invalidate_recordset(['pos_order_count', 'total_order_count'])
                result['loyalty.program'] = self.env['loyalty.program']._load_pos_data_read(
                    programs, config
                )
        return result

    def _process_loyalty(self):
        """Create/credit the loyalty cards involved in this order and record history.

        Every program that takes part in the order goes through a card:
        - points *issued* by the order are recomputed server-side from the rules
        - points *used* are recomputed from the rewards (see loyalty.reward._get_pos_points_cost);
        - one loyalty.history line per card records both.

        :returns: the loyalty.card records created or credited.
        """
        self.ensure_one()
        if not self.config_id:
            return self.env['loyalty.card']

        # Lock processing the same order
        self.lock_for_update()

        if self.env['loyalty.history'].search_count([
            ('order_model', '=', 'pos.order'),
            ('order_id', '=', self.id),
        ]):
            return self.env['loyalty.card']

        programs = self.config_id._get_program_ids(check_usage=False)

        # Lock every card this order may touch
        involved_cards = self.lines.card_id | self.lines.refunded_orderline_id.card_id
        if self.partner_id:
            involved_cards |= self.env['loyalty.card'].search([
                ('program_id', 'in', programs.ids),
                ('partner_id', '=', self.partner_id.id),
            ])
        involved_cards.lock_for_update()

        credited_cards = self.env['loyalty.card']
        LoyaltyHistory = self.env['loyalty.history']
        base_values = {
            'order_model': 'pos.order',
            'order_id': self.id,
            'description': self.name,
        }
        # A balance is read back from the history, so a line spending points has to be created
        # after the ones awarding them: the awards are gathered first, the spending after.
        history_vals = []
        movements = []

        topup_lines = self.lines.filtered(
            lambda l: not l.is_reward_line and not l._is_tip_line() and (
                l._get_loyalty_program() in programs
                or l.refunded_orderline_id.card_id.program_id in programs
            )
        )
        for line in topup_lines:
            card = line.card_id or line.refunded_orderline_id.card_id
            if not card:
                program = line._get_loyalty_program()
                if program.program_type in ('gift_card', 'ewallet'):
                    vals = line.gift_card_vals or {}
                    card = self.env['loyalty.card']._get_or_create_pos_card(
                        program,
                        self.partner_id.id,
                        vals.get('code'),
                        vals.get('expiration_date'),
                        source_order=self,
                    )
                    line.card_id = card
            if not card:
                continue
            origin_line = line.refunded_orderline_id
            if self.is_refund and origin_line:
                # Refunding a topup/gift-card sale: debit the card by what the origin
                # line credited it, prorated by the refunded quantity (line.qty < 0).
                points_issued = (origin_line.qty and (
                    card.program_id._get_pos_order_points(origin_line.order_id, origin_line)
                    * (line.qty / origin_line.qty)
                )) or 0
            else:
                points_issued = card.program_id._get_pos_order_points(self, line)
            if card.program_id.program_type == 'gift_card' and not card.source_pos_order_id:
                card.source_pos_order_id = self.id
                if card.points:
                    points_issued = 0
            credited_cards |= card
            # Selling a gift card that already holds points awards nothing, but the card
            # still gets a row: this order's history is what tells a second run it is done.
            history_vals += LoyaltyHistory._get_history_lines_values(
                card, base_values, points_issued
            ) or [{**base_values, 'card_id': card.id, 'issued': 0, 'used': 0}]

        # The programs below read `card.points`, which only counts the top-ups once their
        # lines exist.
        if history_vals:
            LoyaltyHistory.create(history_vals)
            history_vals = []

        earning_lines = self.lines - topup_lines
        for program in programs:
            reward_lines = self.lines.filtered(
                lambda l: l.is_reward_line and l.reward_id.program_id == program
            )
            reversal_used = 0.0
            if self.is_refund and not program.is_payment_program:
                reversal = self._get_refund_reversal_points(program)
                points_issued = reversal['issued']
                if not reward_lines:
                    reversal_used = reversal['used']
            else:
                points_issued = program._get_pos_order_points(self, earning_lines)

            if (program.applies_on == 'current' and not reward_lines and not self.is_refund) or (
                not points_issued and not reversal_used and not reward_lines
            ):
                continue

            # Enforce the usage limit against the count before this order: total_order_count
            # already includes this order when it carries a reward line, so subtract that so
            # the order reaching the cap is still credited while later orders are skipped.
            if program.limit_usage:
                prior_usage = program.total_order_count - (1 if reward_lines else 0)
                if prior_usage >= program.max_usage:
                    continue

            if self.is_refund and not reward_lines and not program.is_payment_program:
                cards = self._get_refund_reversal_cards(program)
            else:
                cards = self._get_loyalty_cards_to_credit(program, reward_lines)
            if not cards:
                continue

            reward_lines.filtered(lambda l: not l.card_id).card_id = cards[0]

            for card in cards:
                card_lines = reward_lines.filtered(lambda l: l.card_id == card)
                card_issued = points_issued if card == cards[0] else 0
                available_points = card.points + card_issued
                points_used = reversal_used if card == cards[0] else 0.0
                for reward in card_lines.reward_id:
                    lines = card_lines.filtered(lambda l: l.reward_id == reward)
                    cost = reward._get_pos_points_cost(lines, available_points - points_used)
                    points_used += cost
                    lines[0].points_cost = cost
                    lines[1:].points_cost = 0

                if points_used > 0 and float_compare(points_used, available_points, precision_rounding=0.01) > 0:
                    raise UserError(_(
                        "Not enough points to claim the rewards of program '%(program)s'"
                        "(needed: %(needed)s, available: %(available)s). "
                        "Remove the reward lines from the order and validate again.",
                        card=card.code or card.id,
                        program=program.name,
                        needed=points_used,
                        available=available_points,
                    ))

                credited_cards |= card
                if card_issued or points_used:
                    movements += [(card, card_issued), (card, -points_used)]
                else:
                    # A card that moved no points still gets a row, same as a top-up.
                    history_vals.append(
                        {**base_values, 'card_id': card.id, 'issued': 0, 'used': 0}
                    )

        # A refund reverses both directions at once, which flips the sign of each movement:
        # taking earned points back spends them, and returning spent points awards them. The
        # movements are therefore grouped by sign rather than by where they come from, so that
        # the awarding lines always exist before the consuming ones draw on them.
        for awarding in (True, False):
            history_vals += [
                line_values
                for card, points in movements
                if points and (points > 0) is awarding
                for line_values in LoyaltyHistory._get_history_lines_values(
                    card, base_values, points
                )
            ]
            if history_vals:
                LoyaltyHistory.create(history_vals)
                history_vals = []

        new_cards = credited_cards.filtered(lambda c: c.source_pos_order_id == self)
        if new_cards:
            new_cards._send_creation_communication()
        return credited_cards

    def _get_mail_attachments(self, name, ticket, basic_ticket):
        """Attach the gift card report (code/barcode PDF) to the emailed receipt.

        Gift cards sold on this order are printed through their program's
        ``pos_report_print_id`` and appended to the receipt email.
        """
        attachments = super()._get_mail_attachments(name, ticket, basic_ticket)
        gift_card_programs = self.config_id._get_program_ids().filtered(
            lambda p: p.program_type == 'gift_card' and p.pos_report_print_id
        )
        if not gift_card_programs:
            return attachments

        gift_cards = self.env['loyalty.card'].search([
            ('source_pos_order_id', '=', self.id),
            ('program_id', 'in', gift_card_programs.ids),
        ])
        for program in gift_card_programs:
            program_gift_cards = gift_cards.filtered(lambda gc: gc.program_id == program)
            if not program_gift_cards:
                continue
            action_report = program.pos_report_print_id
            report = action_report._render_qweb_pdf(action_report.report_name, program_gift_cards.ids)
            gift_card_pdf = self.env['ir.attachment'].create({
                'name': name + '.pdf',
                'type': 'binary',
                'raw': report[0],
                'res_model': 'pos.order',
                'res_id': self.ids[0],
                'mimetype': 'application/pdf',
            })
            attachments += [(4, gift_card_pdf.id)]

        return attachments

    def _get_refund_reversal_points(self, program):
        """
        Points to reverse for `program` on this refund order, proportional to the
        refunded amount: the earned points are removed spent points are returned.
        mirror of *static/src/app/models/loyalty_program.js* LoyaltyProgram._getRefundReversalPoints
        """
        self.ensure_one()
        refund_lines = self.lines.filtered(
            lambda l: l.refunded_orderline_id and not l.is_reward_line and not l._is_tip_line()
            and not (l.card_id or l.refunded_orderline_id.card_id)
        )
        if not refund_lines:
            return {'issued': 0.0, 'used': 0.0}

        lines_by_origin = defaultdict(lambda: self.env['pos.order.line'])
        for line in refund_lines:
            lines_by_origin[line.refunded_orderline_id.order_id] |= line

        reversal_issued = 0.0
        reversal_used = 0.0
        for origin_order, origin_refund_lines in lines_by_origin.items():
            history = self.env['loyalty.history'].search([
                ('order_model', '=', 'pos.order'),
                ('order_id', '=', origin_order.id),
                ('card_id.program_id', '=', program.id),
            ])
            origin_base = sum(
                origin_order.lines
                .filtered(lambda l: not l.is_reward_line and not l.card_id and not l._is_tip_line())
                .mapped('price_subtotal_incl')
            )
            if not origin_base:
                continue
            refunded_base = 0.0
            for line in origin_refund_lines:
                origin_line = line.refunded_orderline_id
                if not origin_line.qty:
                    continue
                refunded_base += origin_line.price_subtotal_incl * (-line.qty / origin_line.qty)
            ratio = refunded_base / origin_base
            reversal_issued -= sum(history.mapped('issued')) * ratio
            reversal_used -= sum(history.mapped('used')) * ratio

        return {'issued': reversal_issued, 'used': reversal_used}

    def _get_refund_reversal_cards(self, program):
        """
        Cards the original orders credited for `program`.
        """
        origin_orders = self.lines.refunded_orderline_id.order_id
        if not origin_orders:
            return self.env['loyalty.card'].sudo()
        history = self.env['loyalty.history'].search([
            ('order_model', '=', 'pos.order'),
            ('order_id', 'in', origin_orders.ids),
            ('card_id.program_id', '=', program.id),
        ])
        return history.card_id

    def _get_loyalty_cards_to_credit(self, program, reward_lines):
        """Find or create the card(s) that should receive/spend points.

        Reward lines may already reference the cards they spend from (gift cards / eWallets);
        When no line references a card, a nominative program reserves a card to its customer,
        while other programs get a per-order card. The card carries the order's partner (when
        set) so creation communications (next-order coupon emails, ...) have a recipient.
        """
        if reward_lines.card_id:
            return reward_lines.card_id

        LoyaltyCard = self.env['loyalty.card'].with_context(action_no_send_mail=True).sudo()

        if program.is_nominative:
            if not self.partner_id:
                return
            existing = LoyaltyCard.search([
                ('program_id', '=', program.id),
                ('partner_id', '=', self.partner_id.id),
            ], limit=1)
            if existing:
                return existing

        return LoyaltyCard.create({
            'program_id': program.id,
            'partner_id': self.partner_id.id,
            'points': 0,
            'expiration_date': program.date_to or False,
            'source_pos_order_id': self.id,
        })
