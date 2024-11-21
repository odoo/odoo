# -*- coding: utf-8 -*-

from odoo import fields, models


class Notification(models.Model):
    _inherit = 'mail.notification'

    notification_type = fields.Selection(selection_add=[('snail', 'Snailmail')], ondelete={'snail': 'cascade'})
    letter_id = fields.Many2one('snailmail.letter', string="Snailmail Letter", index='btree_not_null', ondelete='cascade')
    failure_type = fields.Selection(selection_add=[
        ('sn_credit', "Snailmail Credit Error"),
        ('sn_trial', "Snailmail Trial Error"),
        ('sn_price', "Snailmail No Price Available"),
        ('sn_fields', "Snailmail Missing Required Fields"),
        ('sn_format', "Snailmail Format Error"),
        ('sn_error', "Snailmail Unknown Error"),
    ])
