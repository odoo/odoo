# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrReferralFriend(models.Model):
    _name = 'hr.referral.friend'
    _description = 'Friends for Referrals'

    name = fields.Char('Friend Name', required=True)
    position = fields.Selection([
        ('front', 'Front'),
        ('back', 'Back')
    ], required=True, default='back', help="Define the position of the friend. If it's a small friend like a dog, you must select Front, it will be placed in the front of the dashboard, above superhero.")
    image = fields.Binary("Dashboard Image", required=True,
        help="This field holds the image used as image for the friend on the dashboard, limited to 1024x1024px.")
    image_head = fields.Binary("Image", required=True,
        help="This field holds the image used as image for the head's friend when the user must choose a new friend, limited to 1024x1024px.")
