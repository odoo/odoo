from odoo import models


class WebsiteSlideMergePartnerAutomatic(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _merge(self, partner_ids, dst_partner=None, extra_checks=True):
        super(WebsiteSlideMergePartnerAutomatic, self)._merge(partner_ids, dst_partner, extra_checks)
        if not dst_partner:
            return

        channel_partners = self.env['slide.channel.partner'].sudo().search([('partner_id', '=', dst_partner.id)],
                                                                           order='completion DESC')
        seen_channel = set()
        to_unlink = self.env['slide.channel.partner']
        for channel_partner in channel_partners:
            if channel_partner.channel_id in seen_channel:
                to_unlink += channel_partner
            else:
                seen_channel.add(channel_partner.channel_id)

        to_unlink.unlink()
