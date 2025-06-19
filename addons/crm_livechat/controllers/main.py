# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.im_livechat.controllers.main import LivechatController
from odoo.http import request
from odoo.addons.mail.tools.discuss import Store


class CrmLivechat(LivechatController):
    def _prepare_visitor_data(self, store, channel, visitor_id):
        user = request.env.user
        if user.has_group('sales_team.group_sale_salesman_all_leads'):
            visitor_partner_id = request.env['website.visitor'].browse(visitor_id).partner_id
        if visitor_partner_id:
            leads = request.env['crm.lead'].search([
                ('partner_id', '=', visitor_partner_id.id),
                ('active', '=', True),
            ])
            store.add(channel, {"crm_leads": Store.Many(leads, ["name"], mode="ADD")})
        return super()._prepare_visitor_data(store, channel, visitor_id)
