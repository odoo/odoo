# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class Partners(models.Model):
    """ Update of res.partners class
        - override name_get to take into account the livechat username
    """
    _inherit = 'res.partner'

    def name_get(self):
        if self.env.context.get('im_livechat_use_username'):
            # process the ones with livechat username
            users_with_livechatname = self.env['res.users'].search([('partner_id', 'in', self.ids), ('livechat_username', '!=', False)])
            map_with_livechatname = {}
            for user in users_with_livechatname:
                map_with_livechatname[user.partner_id.id] = user.livechat_username

            # process the ones without livecaht username
            partner_without_livechatname = self - users_with_livechatname.mapped('partner_id')
            no_livechatname_name_get = super(Partners, partner_without_livechatname).name_get()
            map_without_livechatname = dict(no_livechatname_name_get)

            # restore order
            result = []
            for partner in self:
                name = map_with_livechatname.get(partner.id)
                if not name:
                    name = map_without_livechatname.get(partner.id)
                result.append((partner.id, name))
        else:
            result = super(Partners, self).name_get()
        return result
