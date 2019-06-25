# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class Partner(models.Model):
    _inherit = 'res.partner'

    def _compute_im_status(self):
        #we asume that mail_bot _compute_im_status will be executed after bus _compute_im_status
        super(Partner, self)._compute_im_status()
        odoobot_id = self.env['ir.model.data'].xmlid_to_res_id("base.partner_root")
        for partner in self:
            if partner.id == odoobot_id:
                partner.im_status = 'bot'

    @api.model
    def get_mention_suggestions(self, search, limit=8):
        #add odoobot in mention suggestion when pinging in mail_thread
        [users, partners] = super(Partner, self).get_mention_suggestions(search, limit=limit)
        if len(partners) + len(users) < limit and "odoobot".startswith(search.lower()):
            odoobot = self.env.ref("base.partner_root")
            if not any([elem['id'] == odoobot.id for elem in partners]):
                if odoobot:
                    partners.append({'id': odoobot.id, 'name': odoobot.name, 'email': odoobot.email})
        return [users, partners]

