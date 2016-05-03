# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _order = 'sequence'

    sequence = fields.Integer()
    active = fields.Boolean(default=True)
    name = fields.Char(string='Level Name')
    partner_weight = fields.Integer(string='Level Weight', default=1,
        help="Gives the probability to assign a lead to this partner. (0 means no assignation.)")


class PartnerActivation(models.Model):
    _name = 'res.partner.activation'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(required=True)


class Partner(models.Model):
    _inherit = "res.partner"

    partner_weight = fields.Integer(string='Level Weight',
        help="Gives the probability to assign a lead to this partner. (0 means no assignation.)")
    grade_id = fields.Many2one('res.partner.grade', string='Level')
    activation = fields.Many2one('res.partner.activation', index=1)
    date_partnership = fields.Date(string='Partnership Date')
    date_review = fields.Date(string='Latest Partner Review')
    date_review_next = fields.Date(string='Next Partner Review')
    # customer implementation
    assigned_partner_id = fields.Many2one('res.partner', string='Implemented by')
    implemented_partner_ids = fields.One2many(
        'res.partner', 'assigned_partner_id',
        string='Implementation References'
    )
