# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SurveyUser_Input(models.Model):
    _inherit = 'survey.user_input'

    mass_mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing', readonly=True, index='btree_not_null')
