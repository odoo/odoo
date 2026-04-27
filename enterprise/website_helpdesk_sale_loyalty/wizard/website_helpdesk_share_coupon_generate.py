# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class WebsiteHelpdeskShareCouponGenerate(models.TransientModel):
    _inherit = "helpdesk.sale.coupon.generate"

    def action_coupon_generate_share(self):
        self.ensure_one()
        coupon = self.env['loyalty.card'].sudo().create({
            'partner_id': self.ticket_id.partner_id.id,
            'program_id': self.program.id,
            'points': self.points_granted,
            'expiration_date': self.valid_until,
        })
        self.ticket_id.coupon_ids |= coupon
        return self.env['coupon.share'].create_share_action(coupon=coupon)
