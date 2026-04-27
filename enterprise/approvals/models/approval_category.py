# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


CATEGORY_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None')]


class ApprovalCategory(models.Model):
    _name = 'approval.category'
    _description = 'Approval Category'
    _order = 'sequence, id'

    _check_company_auto = True

    def _get_default_image(self):
        default_image_path = 'approvals/static/src/img/Folder.png'
        return base64.b64encode(tools.misc.file_open(default_image_path, 'rb').read())

    name = fields.Char(string="Name", translate=True, required=True)
    company_id = fields.Many2one(
        'res.company', 'Company', copy=False,
        required=True, index=True, default=lambda s: s.env.company)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(string="Sequence")
    description = fields.Char(string="Description", translate=True)
    image = fields.Binary(string='Image', default=_get_default_image)
    has_date = fields.Selection(CATEGORY_SELECTION, string="Has Date", default="no", required=True)
    has_period = fields.Selection(CATEGORY_SELECTION, string="Has Period", default="no", required=True)
    has_quantity = fields.Selection(CATEGORY_SELECTION, string="Has Quantity", default="no", required=True)
    has_amount = fields.Selection(CATEGORY_SELECTION, string="Has Amount", default="no", required=True)
    has_reference = fields.Selection(
        CATEGORY_SELECTION, string="Has Reference", default="no", required=True,
        help="An additional reference that should be specified on the request.")
    has_partner = fields.Selection(CATEGORY_SELECTION, string="Has Contact", default="no", required=True)
    has_payment_method = fields.Selection(CATEGORY_SELECTION, string="Has Payment", default="no", required=True)
    has_location = fields.Selection(CATEGORY_SELECTION, string="Has Location", default="no", required=True)
    has_product = fields.Selection(
        CATEGORY_SELECTION, string="Has Product", default="no", required=True,
        help="Additional products that should be specified on the request.")
    requirer_document = fields.Selection([('required', 'Required'), ('optional', 'Optional')], string="Documents", default="optional", required=True)
    approval_minimum = fields.Integer(string="Minimum Approval", default="1", required=True)
    invalid_minimum = fields.Boolean(compute='_compute_invalid_minimum')
    invalid_minimum_warning = fields.Char(compute='_compute_invalid_minimum')
    approval_type = fields.Selection(string="Approval Type", selection=[],
        help="Allows you to define which documents you would like to create once the request has been approved")
    manager_approval = fields.Selection([('approver', 'Is Approver'), ('required', 'Is Required Approver')],
        string="Employee's Manager",
        help="""How the employee's manager interacts with this type of approval.

        Empty: do nothing
        Is Approver: the employee's manager will be in the approver list
        Is Required Approver: the employee's manager will be required to approve the request.
    """)
    user_ids = fields.Many2many('res.users', compute='_compute_user_ids', string="Approver Users")
    approver_ids = fields.One2many('approval.category.approver', 'category_id', string="Approvers")
    approver_sequence = fields.Boolean('Approvers Sequence?', help="If checked, the approvers have to approve in sequence (one after the other). If Employee's Manager is selected as approver, they will be the first in line.")
    request_to_validate_count = fields.Integer("Number of requests to validate", compute="_compute_request_to_validate_count")
    automated_sequence = fields.Boolean('Automated Sequence?',
        help="If checked, the Approval Requests will have an automated generated name based on the given code.")
    sequence_code = fields.Char(string="Code")
    sequence_id = fields.Many2one('ir.sequence', 'Reference Sequence',
        copy=False, check_company=True)

    def _compute_request_to_validate_count(self):
        domain = [('request_status', '=', 'pending'), ('approver_ids.user_id', '=', self.env.user.id)]
        requests_data = self.env['approval.request']._read_group(domain, ['category_id'], ['__count'])
        requests_mapped_data = {category.id: count for category, count in requests_data}
        for category in self:
            category.request_to_validate_count = requests_mapped_data.get(category.id, 0)

    @api.depends_context('lang')
    @api.depends('approval_minimum', 'approver_ids', 'manager_approval')
    def _compute_invalid_minimum(self):
        for record in self:
            if record.approval_minimum > len(record.approver_ids) + int(bool(record.manager_approval)):
                record.invalid_minimum = True
            else:
                record.invalid_minimum = False
            record.invalid_minimum_warning = record.invalid_minimum and _('Your minimum approval exceeds the total of default approvers.')

    @api.depends('approver_ids')
    def _compute_user_ids(self):
        for record in self:
            record.user_ids = record.approver_ids.user_id

    @api.constrains('approval_minimum', 'approver_ids')
    def _constrains_approval_minimum(self):
        for record in self:
            if record.approval_minimum < len(record.approver_ids.filtered('required')):
                raise ValidationError(_('Minimum Approval must be equal or superior to the sum of required Approvers.'))

    @api.constrains('approver_ids')
    def _constrains_approver_ids(self):
        # There seems to be a problem with how the database is updated which doesn't let use to an sql constraint for this
        # Issue is: records seem to be created before others are saved, meaning that if you originally have only user a
        #  change user a to user b and add a new line with user a, the second line will be created and will trigger the constraint
        #  before the first line will be updated which wouldn't trigger a ValidationError
        for record in self:
            if len(record.approver_ids) != len(record.approver_ids.user_id):
                raise ValidationError(_('An user may not be in the approver list multiple times.'))

    @api.constrains('approver_sequence', 'approval_minimum')
    def _constrains_approver_sequence(self):
        if any(a.approver_sequence and not a.approval_minimum for a in self):
            raise ValidationError(_('Approver Sequence can only be activated with at least 1 minimum approver.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('automated_sequence'):
                sequence = self.env['ir.sequence'].create({
                    'name': _('Sequence %(code)s', code=vals['sequence_code']),
                    'padding': 5,
                    'prefix': vals['sequence_code'],
                    'company_id': vals.get('company_id'),
                })
                vals['sequence_id'] = sequence.id
        return super().create(vals_list)

    def write(self, vals):
        if 'sequence_code' in vals:
            for approval_category in self:
                sequence_vals = {
                    'name': _('Sequence %(code)s', code=vals['sequence_code']),
                    'padding': 5,
                    'prefix': vals['sequence_code'],
                }
                if approval_category.sequence_id:
                    approval_category.sequence_id.write(sequence_vals)
                else:
                    sequence_vals['company_id'] = vals.get('company_id', approval_category.company_id.id)
                    sequence = self.env['ir.sequence'].create(sequence_vals)
                    approval_category.sequence_id = sequence
        if 'company_id' in vals:
            for approval_category in self:
                if approval_category.sequence_id:
                    approval_category.sequence_id.company_id = vals.get('company_id')
        return super().write(vals)

    def create_request(self):
        self.ensure_one()
        # If category uses sequence, set next sequence as name
        # (if not, set category name as default name).
        return {
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "views": [[False, "form"]],
            "context": {
                'default_name': _('New') if self.automated_sequence else self.name,
                'default_category_id': self.id,
                'default_request_owner_id': self.env.user.id,
                'default_request_status': 'new'
            },
        }
