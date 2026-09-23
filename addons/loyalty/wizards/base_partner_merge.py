from odoo import models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _update_foreign_keys(self, src_partners, dst_partner):
        """Override of base to merge corresponding nominative loyalty cards."""
        self._merge_loyalty_cards(src_partners, dst_partner)
        super()._update_foreign_keys(src_partners, dst_partner)

    def _merge_loyalty_cards(self, src_partners, dst_partner):
        """Merge nominative loyalty cards.

        Each program's points end up on one card held by `dst_partner`, and both
        sides of the move are written to `loyalty.history` -- otherwise the
        surviving balance is right and nothing explains it.

        :param src_partners: recordset of source res.partner records to merge
        :param dst_partner: destination res.partner record
        """
        LoyaltyCard = self.env["loyalty.card"].sudo()
        cards_per_program = dict(
            LoyaltyCard._read_group(
                domain=[
                    ("partner_id", "in", src_partners.ids),
                    # `loyalty.program` owns what "nominative" means; this used to
                    # be a second copy of `_compute_is_nominative`'s condition.
                    ("program_id.is_nominative", "=", True),
                ],
                groupby=["program_id"],
                aggregates=["id:recordset"],
            )
        )
        if not cards_per_program:
            return

        # One search for every destination card rather than one per program.
        destination_per_program = {}
        for card in LoyaltyCard.search(
            [
                ("partner_id", "=", dst_partner.id),
                ("program_id", "in", [program.id for program in cards_per_program]),
            ],
            order="id",
        ):
            destination_per_program.setdefault(card.program_id, card)

        history_vals = []
        for program, cards in cards_per_program.items():
            # `id:recordset` promises no order: keep the oldest card, so the one
            # that survives is the one whose history reaches furthest back.
            cards = cards.sorted("id")
            survivor = destination_per_program.get(program) or cards[0]
            drained = cards - survivor
            moved = sum(drained.mapped("points"))

            history_vals.extend(
                {
                    "card_id": card.id,
                    "description": self.env._(
                        "Merged into %s", dst_partner.display_name
                    ),
                    "used": card.points,
                }
                for card in drained
                if card.points
            )
            if moved:
                history_vals.append(
                    {
                        "card_id": survivor.id,
                        "description": self.env._(
                            "Merged from %s",
                            ", ".join(drained.partner_id.mapped("display_name")),
                        ),
                        "issued": moved,
                    }
                )

            survivor.write(
                {"partner_id": dst_partner.id, "points": survivor.points + moved}
            )
            drained.write({"points": 0, "active": False})

        self.env["loyalty.history"].sudo().create(history_vals)
