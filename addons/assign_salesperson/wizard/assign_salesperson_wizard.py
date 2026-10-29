# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.
from odoo import models, api, fields


class AssignSalesPerson(models.Model):
    _name = 'assign.sales.person'
    
    user_ids = fields.Many2many('res.users', string='Salesperson')

    # check sales person base on record id
    def chunkIt(self, seq, num):
        avg = len(seq) / float(num)
        out = []
        last = 0.0
        while last < len(seq):
            out.append(seq[int(last):int(last + avg)])
            last += avg
        return out
    
    # Assign salesperson methods
    def salesperson_assign(self):
        leads = self.chunkIt(self._context.get('active_ids'), len(self.user_ids.ids))
        counter = 0
        crm_lead_obj = self.env['crm.lead']
        for user in self.user_ids:
            crm_lead_rec = crm_lead_obj.browse(leads[counter])
            crm_lead_rec.with_context(mail_auto_subscribe_no_notify=1).write({'user_id': user.id})
            counter += 1
        return True
