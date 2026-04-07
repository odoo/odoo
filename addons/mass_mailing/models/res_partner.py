# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _mailing_enabled = True

    mailing_contact_id = fields.One2many('mailing.contact', 'res_partner_id')

    def action_add_to_mailing_list(self):
        ctx = dict(self.env.context, default_partner_ids=self.ids)
        action = self.env["ir.actions.actions"]._for_xml_id("mass_mailing.contact_to_mailing_list_action")
        action['view_mode'] = 'form'
        action['target'] = 'new'
        action['context'] = ctx | json.loads(action['context'])

        return action

    def action_view_mailing_contact(self):
        action = self.env['ir.actions.act_window']._for_xml_id('mass_mailing.action_view_mass_mailing_contacts')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.mailing_contact_id.id

        return action
