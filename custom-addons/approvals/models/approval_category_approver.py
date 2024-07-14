# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ApprovalCategoryApprover(models.Model):
    """ Intermediate model between approval.category and res.users
        To know whether an approver for this category is required or not
    """
    _name = 'approval.category.approver'
    _description = 'Approval Type Approver'
    _rec_name = 'user_id'
    _order = 'sequence'

    sequence = fields.Integer('Sequence', default=10)
    category_id = fields.Many2one('approval.category', string='Approval Type', ondelete='cascade', required=True)
    company_id = fields.Many2one('res.company', related='category_id.company_id')
    user_id = fields.Many2one('res.users', string='User', ondelete='cascade', required=True,
        check_company=True, domain="[('company_ids', 'in', company_id), ('id', 'not in', existing_user_ids)]")
    required = fields.Boolean(default=False)

    existing_user_ids = fields.Many2many('res.users', compute='_compute_existing_user_ids')

    @api.depends('category_id')
    def _compute_existing_user_ids(self):
        for record in self:
            record.existing_user_ids = record.category_id.approver_ids.user_id
