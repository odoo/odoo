# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools import float_compare

FIFO_ORDER = "expiration_date ASC NULLS LAST, points_changed_date ASC, id ASC"


class LoyaltyHistory(models.Model):
    """Records of point movements for loyalty cards and eWallets.

    Each row is one of:
    - Award: issued > 0, without a linked line, and with an expiration date when the program
      expires points.
    - Consumption: used > 0, with a linked line (the award line whose points are being
      consumed), and therefore expiring along with it.
    - Debt: used > 0, without a linked line (a consumption whose award was deleted, hence
      never expires).

    A line either awards or consumes points, never both.

    A consumption becomes a debt when its linked award is deleted, which happens when an
    order that awarded points is cancelled after those points were spent. Conversely, a debt
    becomes a consumption once it finds awards covering it, which happens when an order that
    consumed points is cancelled or when a new order awarding points is confirmed.
    Since a consumption draws from a single award, a debt covered by several awards is split into
    one consumption per award.
    """

    _name = "loyalty.history"
    _description = "History for Loyalty cards and Ewallets"
    _order = "points_changed_date desc, id desc"

    card_id = fields.Many2one(
        comodel_name="loyalty.card", ondelete="cascade", readonly=True, required=True, index=True
    )
    company_id = fields.Many2one(related="card_id.company_id")
    program_type = fields.Selection(related="card_id.program_type")
    linked_loyalty_history_id = fields.Many2one(
        comodel_name="loyalty.history", readonly=True, index=True
    )

    description = fields.Text(readonly=True, required=True)

    issued = fields.Float(readonly=True)
    used = fields.Float(readonly=True)
    # The date these points were awarded or spent, kept apart from `create_date` because a
    # line can be deleted and recreated long after the points actually moved.
    points_changed_date = fields.Datetime(
        string="Date", default=fields.Datetime.now, readonly=True, required=True
    )
    expiration_date = fields.Date(readonly=True, index=True)

    order_model = fields.Char(readonly=True)
    order_id = fields.Many2oneReference(model_field="order_model", readonly=True)

    _issued_or_used = models.Constraint(
        "CHECK (issued = 0 OR used = 0)",
        "A history line either awards or consumes points, never both.",
    )
    _issued_and_used_positive = models.Constraint(
        "CHECK (issued >= 0 AND used >= 0)",
        "A history line cannot award or consume a negative amount of points.",
    )

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (
                vals.get("issued", 0) > 0
                and not vals.get("linked_loyalty_history_id")
                and "expiration_date" not in vals
            ):
                card = self.env["loyalty.card"].browse(vals.get("card_id"))
                if card.program_type == "loyalty" and card.program_id.expire_after:
                    vals["expiration_date"] = fields.Date.today() + timedelta(
                        days=card.program_id.expire_after
                    )
        send_mail = not self.env.context.get("loyalty_no_mail", False)
        cards = self.env["loyalty.card"]
        points_before = {}
        if send_mail:
            cards = self.env["loyalty.card"].browse({
                vals["card_id"] for vals in vals_list if vals.get("card_id")
            })
            points_before = self._get_points_by_card(cards)
        result = super().create(vals_list)
        if send_mail and cards:
            points_after = self._get_points_by_card(cards)
            points_changes = {
                card: {"old": points_before[card], "new": points_after[card]} for card in cards
            }
            cards._send_points_reach_communication(points_changes)
        # The awards just created may cover debts that nothing could cover until now.
        awarded_cards = result.filtered(lambda history: history.issued > 0).card_id
        if awarded_cards:
            self._settle_outstanding_debt(awarded_cards)
        return result

    def unlink(self):
        affected_cards = self.card_id
        result = super().unlink()
        # Consumptions that drew from a deleted award are now debts, try to draw those points from
        # the awards that are left.
        if affected_cards:
            self._settle_outstanding_debt(affected_cards)
        return result

    # === BUSINESS METHODS === #

    def _get_order_portal_url(self):
        self.ensure_one()
        return False

    def _get_order_description(self):
        self.ensure_one()
        return self.env[self.order_model].browse(self.order_id).display_name

    @api.model
    def _get_points_by_card(self, loyalty_cards):
        """Return points computed directly from history rows.

        :param loyalty.card loyalty_cards: loyalty cards to compute the balance for.
        :return: points per loyalty card
        :rtype: dict
        """
        points_per_card = {
            card: issued - used for card, issued, used in self._get_points_data(loyalty_cards)
        }
        return {card: points_per_card.get(card, 0.0) for card in loyalty_cards}

    @api.model
    def _get_points_data(self, cards=None):
        """Return issued/used sums per card from history rows that still count
        towards a card's balance.

        :param loyalty.card cards: cards to sum the rows of, all of them when not given
        :return: card, issued sum and used sum, per card
        :rtype: list
        """
        today = fields.Date.today()
        domain = Domain.AND([
            Domain.OR([
                Domain("expiration_date", "=", False),
                Domain("expiration_date", ">=", today),
            ]),
            Domain.OR([
                Domain("linked_loyalty_history_id", "=", False),
                Domain("linked_loyalty_history_id.expiration_date", "=", False),
                Domain("linked_loyalty_history_id.expiration_date", ">=", today),
            ]),
        ])
        if cards:
            domain = Domain.AND([Domain("card_id", "in", cards.ids), domain])
        return self._read_group(
            domain=domain, groupby=["card_id"], aggregates=["issued:sum", "used:sum"]
        )

    @api.model
    def _get_points_left_per_award(self, cards):
        """Return the award lines of `cards` that can still be drawn from.

        :param loyalty.card cards: cards to look for awards on
        :return: the unexpired awards, oldest first, and what is left on each of them
        :rtype: tuple
        """
        awards = self.search(
            [
                ("card_id", "in", cards.ids),
                ("issued", ">", 0),
                "|",
                ("expiration_date", "=", False),
                ("expiration_date", ">=", fields.Date.today()),
            ],
            order=FIFO_ORDER,
        )
        drawn_per_award = dict(
            self._read_group(
                domain=[("linked_loyalty_history_id", "in", awards.ids)],
                groupby=["linked_loyalty_history_id"],
                aggregates=["used:sum"],
            )
        )
        return awards, {award: award.issued - drawn_per_award.get(award, 0.0) for award in awards}

    @api.model
    def _draw_points_from_awards(self, awards, points_left, points, values):
        """Return the consuming lines drawing `points` from `awards`, oldest first.

        :param loyalty.history awards: award lines to draw from, oldest first
        :param dict points_left: points still on each award, decreased by what is drawn
        :param float points: points to draw
        :param dict values: base values for the returned line(s)
        :return: creation values for the consuming lines, and the points left to draw
        :rtype: tuple
        """
        create_vals = []
        for award in awards:
            if float_compare(points, 0, precision_digits=2) <= 0:
                break
            if float_compare(points_left[award], 0, precision_digits=2) <= 0:
                continue
            drawn = min(points_left[award], points)
            create_vals.append({**values, "used": drawn, "linked_loyalty_history_id": award.id})
            points_left[award] -= drawn
            points -= drawn
        return create_vals, points

    @api.model
    def _settle_outstanding_debt(self, cards):
        """Draw outstanding debt lines from the award lines that can now cover them.

        A debt is a consumption line whose award was deleted. Being unlinked, it never
        expires, so it keeps weighing on the balance forever. Since a consumption line draws
        from a single award, a debt is replaced by one consumption per award it draws from,
        and whatever no award can cover stays behind as a smaller debt line.

        :param loyalty.card cards: cards to re-attempt debt settlement on
        """
        if self.env.context.get("loyalty_settling_debt"):
            return
        # Settling is bookkeeping the user never asks for, and no group may delete history
        # lines, so it runs with elevated rights.
        history_sudo = self.sudo().with_context(loyalty_settling_debt=True, loyalty_no_mail=True)
        cards = cards.filtered(lambda c: c.program_type == "loyalty")
        # Every card is settled in one pass: reading the lines card by card would make an
        # upgrade, or a session closing many orders at once, issue queries per card.
        debts = history_sudo.search(
            [
                ("card_id", "in", cards.ids),
                ("used", ">", 0),
                ("linked_loyalty_history_id", "=", False),
            ],
            order=FIFO_ORDER,
        )
        if not debts:
            return
        awards, points_left = history_sudo._get_points_left_per_award(debts.card_id)
        awards_per_card = awards.grouped("card_id")

        create_vals = []
        settled_debt_ids = []
        for debt in debts:
            base_values = {
                "card_id": debt.card_id.id,
                "description": debt.description,
                "order_model": debt.order_model,
                "order_id": debt.order_id,
                "points_changed_date": debt.points_changed_date,
                "issued": 0,
            }
            debt_vals, left_to_draw = history_sudo._draw_points_from_awards(
                awards_per_card.get(debt.card_id, history_sudo.browse()),
                points_left,
                debt.used,
                base_values,
            )
            if not debt_vals:
                continue
            if float_compare(left_to_draw, 0, precision_digits=2) > 0:
                debt_vals.append({**base_values, "used": left_to_draw})
            create_vals += debt_vals
            settled_debt_ids.append(debt.id)
        if create_vals:
            history_sudo.create(create_vals)
            history_sudo.browse(settled_debt_ids).unlink()

    @api.model
    def _get_history_lines_values(self, card, values, points):
        """Return the creation values for a point movement on a card.

        A positive `points` awards points, a negative one consumes them. Values are
        returned instead of created so that callers looping over cards can create every
        line in a single batch.

        Consumed points are drawn from the unexpired awards they consume, oldest first, so
        a single movement can need several lines, and whatever no award covers is recorded
        as a debt. A caller that both awards and consumes must therefore create the awarding
        lines before asking for the consuming ones, since the latter draw from the former.

        :param loyalty.card card: card to move points on.
        :param dict values: base values for the returned line(s)
        :param float points: points to award (positive) or to consume (negative)
        :return: creation values for `loyalty.history`
        :rtype: list
        """
        card.ensure_one()
        if not points:
            return []
        base_values = {**values, "card_id": card.id}
        if points > 0:
            # Awarded points stand on their own; `_settle_outstanding_debt` draws whatever
            # debt they can cover from them once they exist.
            return [{**base_values, "issued": points, "used": 0}]

        points = -points
        base_values["issued"] = 0
        if card.program_type != "loyalty":
            return [{**base_values, "used": points}]

        awards, points_left = self._get_points_left_per_award(card)
        create_vals, points_left_to_draw = self._draw_points_from_awards(
            awards, points_left, points, base_values
        )
        if float_compare(points_left_to_draw, 0, precision_digits=2) > 0:
            # Whatever no award covers is left unlinked, so it never expires either.
            create_vals.append({**base_values, "used": points_left_to_draw})
        return create_vals
