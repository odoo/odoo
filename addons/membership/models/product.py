# -*- coding: utf-8 -*-

from openerp import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_membership = fields.Boolean('Membership', help='Check if the product is eligible for membership.', oldname='membership')
    membership_date_from = fields.Date('Membership Start Date', help='Date from which membership becomes active.')
    membership_date_to = fields.Date('Membership End Date', help='Date until which membership remains active.')

    _sql_constraints = [
        ('membership_date_greater', 'check(membership_date_to >= membership_date_from)', 'Error! Ending date must be greater than the beginning date.')]
