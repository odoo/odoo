# -*- coding: utf-8 -*-

from openerp import fields, models


class CrmClaimFollowup(models.Model):

    _name = 'crm.claim.followup'
    _description = "Claim Followup"

    date = fields.Date(default=fields.Date.today, required=True)
    action = fields.Char(required=True)
    user_id = fields.Many2one('res.users', string="Responsible", required=True)
    claim_id = fields.Many2one('crm.claim', string="Claim")
