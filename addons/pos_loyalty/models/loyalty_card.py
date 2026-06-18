# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class LoyaltyCard(models.Model):
    _name = 'loyalty.card'
    _inherit = ['loyalty.card', 'pos.load.mixin']

    source_pos_order_id = fields.Many2one(
        string="POS Order Reference",
        help="The POS order from which coupon is generated",
        comodel_name="pos.order",
        readonly=True,
        index="btree_not_null",
    )

    @api.model
    def _load_pos_data_domain(self, data, config):
        return False

    @api.model
    def _load_pos_data_fields(self, config):
        return ['partner_id', 'code', 'points', 'points_display', 'program_id', 'expiration_date', 'write_date', 'source_pos_order_id']

    def _has_source_order(self):
        return super()._has_source_order() or bool(self.source_pos_order_id)

    def _is_new_receipt_coupon(self, orders):
        """
        Whether this card is a coupon ``orders`` issued for a *future* order, to be
        printed with a barcode on the receipt.
        """
        self.ensure_one()
        return (
            self.source_pos_order_id in orders
            and self.program_id.applies_on == 'future'
            and self.program_id.program_type not in ('gift_card', 'ewallet')
        )

    def _compute_use_count(self):
        super()._compute_use_count()
        read_group_res = self.env['pos.order.line']._read_group(
            [('card_id', 'in', self.ids)], ['card_id'], ['__count'])
        count_per_card = {card.id: count for card, count in read_group_res}
        for card in self:
            card.use_count += count_per_card.get(card.id, 0)

    @api.model
    def get_card_status(self, code, config_id):
        config = self.env['pos.config'].browse(config_id)
        card = self.search([('code', '=', code)], limit=1)
        in_config = card.program_id.id in config._get_program_ids().ids
        is_valid_gift_card = card and in_config and (not card.expiration_date or card.expiration_date >= fields.Date.context_today(self)) and card.points > 0
        is_valid_gift_card = is_valid_gift_card and (card.program_id.program_type == 'gift_card') and not card.partner_id
        is_valid_gift_card = is_valid_gift_card and len([id for id in card.history_ids.mapped('order_id') if id != 0]) == 0
        card_fields = self._load_pos_data_fields(config_id)

        return {
            'status': bool(is_valid_gift_card) or not card,
            'loyalty.card': card.read(card_fields, load=False) if in_config else [],
            'has_source_order': card._has_source_order() if in_config else False,
        }

    def _get_or_create_pos_card(self, program, partner_id=False, code=False, expiration_date=False, source_order=False):
        """
        Get, or create if needed, the loyalty card a POS funding line targets.
        """
        LoyaltyCard = self.env['loyalty.card'].with_context(action_no_send_mail=True).sudo()
        if program.is_nominative:
            if not partner_id:
                raise UserError(_("A customer is required to create a %s card.", program.name))
            card = LoyaltyCard.search([
                ('program_id', '=', program.id),
                ('partner_id', '=', partner_id),
            ], limit=1)
            if card:
                return card
        elif code:
            card = LoyaltyCard.search([('code', '=', code)], limit=1)
            if card:
                return card
        vals = {
            'program_id': program.id,
            'partner_id': partner_id,
            'points': 0,
            'expiration_date': expiration_date or program.date_to or False,
        }
        if code:
            vals['code'] = code
        if source_order:
            vals['source_pos_order_id'] = source_order.id
        return LoyaltyCard.create(vals)

    def _send_creation_communication(self, force_send=False):
        """Override to log a sold gift card's email in its source pos.order's chatter."""
        mail_ids = super()._send_creation_communication(force_send=force_send)
        for mail in self.env['mail.mail'].browse([mid for mid in mail_ids if mid]):
            if mail.model != 'loyalty.card' or mail.res_id not in self.ids:
                continue
            card = self.browse(mail.res_id)
            if card.program_id.program_type == 'gift_card' and card.source_pos_order_id:
                card.source_pos_order_id.message_post(body=mail.body_content)
        return mail_ids
