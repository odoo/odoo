from odoo import models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _update_foreign_keys(self, src_partners, dst_partner):
        """ Override of base to merge corresponding nominative loyalty cards."""
        self._merge_loyalty_cards(src_partners, dst_partner)
        super()._update_foreign_keys(src_partners, dst_partner)

    def _merge_loyalty_cards(self, src_partners, dst_partner):
        """ Merge nominative loyalty cards.

        :param src_partners: recordset of source res.partner records to merge
        :param dst_partner: destination res.partner record
        """
        LoyaltyCard = self.env['loyalty.card'].sudo()
        cards_per_program = dict(
            LoyaltyCard._read_group(
                domain=[
                    ('partner_id', 'in', src_partners.ids),
                    '|',
                        ('program_id.applies_on', '=', 'both'),
                        '&',
                            ('program_id.program_type', 'in', ('ewallet', 'loyalty')),
                            ('program_id.applies_on', '=', 'future'),
                ],
                groupby=['program_id'],
                aggregates=['id:recordset'],
            )
        )
        for program, cards in cards_per_program.items():
            total_points = sum(card.points for card in cards)
            dst_card = LoyaltyCard.search([
                ('partner_id', '=', dst_partner.id),
                ('program_id', '=', program.id),
            ], limit=1)
            if dst_card:
                final_card = dst_card
                total_points += dst_card.points
            else:
                final_card = cards[0]
            final_card.sudo().write({'partner_id': dst_partner.id, 'points': total_points})
            (cards - final_card).sudo().write({'points': 0, 'active': False})
