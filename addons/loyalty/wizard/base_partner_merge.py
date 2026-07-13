from odoo import models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = "base.partner.merge.automatic.wizard"

    def _update_foreign_keys(self, src_partners, dst_partner):
        """Override of base to merge corresponding nominative loyalty cards."""
        self._merge_loyalty_cards(src_partners, dst_partner)
        super()._update_foreign_keys(src_partners, dst_partner)

    def _merge_loyalty_cards(self, src_partners, dst_partner):
        """Merge nominative loyalty cards.

        :param res.partner src_partners: source partner records to merge
        :param res.partner dst_partner: destination partner record
        """
        LoyaltyCard = self.env["loyalty.card"].sudo()
        cards_per_program = dict(
            LoyaltyCard._read_group(
                domain=[
                    ("partner_id", "in", src_partners.ids),
                    "|",
                    ("program_id.applies_on", "=", "both"),
                    "&",
                    ("program_id.program_type", "in", ("ewallet", "loyalty")),
                    ("program_id.applies_on", "=", "future"),
                ],
                groupby=["program_id"],
                aggregates=["id:recordset"],
            )
        )
        for program, cards in cards_per_program.items():
            dst_card = LoyaltyCard.search(
                [("partner_id", "=", dst_partner.id), ("program_id", "=", program.id)], limit=1
            )
            final_card = dst_card or cards[0]
            cards_to_archive = cards - final_card
            cards_to_archive.history_ids.write({"card_id": final_card.id})
            final_card.write({"partner_id": dst_partner.id})
            cards_to_archive.write({"active": False})
