# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _, Command


class HrContractSignDocumentWizard(models.TransientModel):
    _name = 'hr.contract.sign.document.wizard'
    _description = 'Sign document in contract'

    def _group_hr_contract_domain(self):
        group = self.env.ref('hr_contract.group_hr_contract_manager', raise_if_not_found=False)
        return [('groups_id', 'in', group.ids)] if group else []

    def _get_sign_template_ids(self):
        list_template = self.env['sign.template']
        for template in self.env['sign.template'].search([]):
            distinct_responsible_count = len(template.sign_item_ids.mapped('responsible_id'))
            if distinct_responsible_count == 2 or distinct_responsible_count == 1:
                list_template |= template
        return list_template

    def _default_get_template_warning(self):
        return not bool(self._get_sign_template_ids()) and _('No appropriate template could be found, please make sure you configured them properly.')

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'responsible_id' in fields_list and not defaults.get('responsible_id') and defaults.get('contract_id'):
            contract = self.env['hr.contract'].browse(defaults.get('contract_id'))
            defaults['responsible_id'] = contract.hr_responsible_id
        else:
            defaults['responsible_id'] = self.env.user
        active_model = self.env.context.get('active_model', '')
        if active_model == 'hr.contract':
            defaults['contract_id'] = self.env.context.get('active_id')
        elif active_model == 'hr.employee':
            defaults['employee_ids'] = [Command.set(self.env.context.get('active_ids'))]
        return defaults

    contract_id = fields.Many2one(
        'hr.contract', string='Contract',
        compute='_compute_contract_id', store=True, readonly=False)
    employee_ids = fields.Many2many(
        'hr.employee', string='Employees',
        compute='_compute_employee_ids', store=True, readonly=False)
    responsible_id = fields.Many2one('res.users', string='Responsible', domain=_group_hr_contract_domain)
    employee_role_id = fields.Many2one(
        "sign.item.role", string="Employee Role",
        required=True, domain="[('id', 'in', sign_template_responsible_ids)]",
        compute='_compute_employee_role_id', store=True, readonly=False,
        help="Employee's role on the templates to sign. The same role must be present in all the templates")
    sign_template_responsible_ids = fields.Many2many(
        'sign.item.role', compute='_compute_responsible_ids')
    possible_template_ids = fields.Many2many('sign.template', compute='_compute_possible_template_ids')
    sign_template_ids = fields.Many2many(
        'sign.template', string='Documents to sign',
        domain="[('id', 'in', possible_template_ids)]", help="""Documents to sign. Only documents with 1 or 2 different responsible are selectable.
        Documents with 1 responsible will only have to be signed by the employee while documents with 2 different responsible will have to be signed by both the employee and the responsible.
        """, required=True)
    has_both_template = fields.Boolean(compute='_compute_has_both_template')
    template_warning = fields.Char(default=_default_get_template_warning, store=False)

    subject = fields.Char(string="Subject", required=True, default='Signature Request')
    message = fields.Html("Message")
    cc_partner_ids = fields.Many2many('res.partner', string="Copy to")
    attachment_ids = fields.Many2many('ir.attachment')
    mail_to = fields.Selection([
        ('work', 'Work'),
        ('private', 'Private'),
    ], string='Email', help="""Email used to send the signature request.
                - Work takes the email defined in "work email"
                - Private takes the email defined in Private Information
                - If the selected email is not defined, the available one will be used.""", default='work')
    mail_displayed = fields.Char(compute='_compute_mail_displayed')

    @api.depends('sign_template_responsible_ids')
    def _compute_employee_role_id(self):
        for wizard in self:
            if wizard.employee_role_id not in wizard.sign_template_responsible_ids:
                wizard.employee_role_id = False
            if len(wizard.sign_template_responsible_ids) == 1:
                wizard.employee_role_id = wizard.sign_template_responsible_ids._origin

    @api.depends('sign_template_ids.sign_item_ids.responsible_id')
    def _compute_responsible_ids(self):
        for r in self:
            responsible_ids = self.env['sign.item.role']
            for sign_template_id in r.sign_template_ids:
                if responsible_ids:
                    responsible_ids &= sign_template_id.sign_item_ids.responsible_id
                else:
                    responsible_ids |= sign_template_id.sign_item_ids.responsible_id
            r.sign_template_responsible_ids = responsible_ids

    @api.depends('sign_template_ids')
    def _compute_possible_template_ids(self):
        possible_sign_templates = self._get_sign_template_ids()
        for wizard in self:
            if not wizard.sign_template_ids:
                wizard.possible_template_ids = possible_sign_templates
            else:
                roles = wizard.sign_template_ids.sign_item_ids.responsible_id
                wizard.possible_template_ids = possible_sign_templates.filtered(lambda t: t.sign_item_ids.responsible_id & roles)

    @api.depends('contract_id')
    def _compute_employee_ids(self):
        for wizard in self:
            if wizard.contract_id:
                wizard.employee_ids |= wizard.contract_id.employee_id

    @api.depends('employee_ids')
    def _compute_contract_id(self):
        for wizard in self:
            if wizard.contract_id.employee_id not in wizard.employee_ids:
                wizard.contract_id = False

    @api.depends('sign_template_ids')
    def _compute_has_both_template(self):
        for wizard in self:
            wizard.has_both_template = bool(wizard.sign_template_ids.filtered(lambda t: len(t.sign_item_ids.mapped('responsible_id')) == 2))

    @api.depends('employee_ids', 'mail_to')
    def _compute_mail_displayed(self):
        for wizard in self:
            if len(wizard.employee_ids) == 1:
                wizard.mail_displayed = wizard.employee_ids.private_email if self.mail_to == 'private' else wizard.employee_ids.work_email
            else:
                wizard.mail_displayed = False

    def validate_signature(self):
        self.ensure_one()
        # Partner by employee
        partner_by_employee = dict()
        for employee in self.employee_ids:
            email_choice = employee.private_email if self.mail_to == "private" else employee.work_email
            if email_choice:
                email_used = email_choice
            else:
                message_display = _("%s does not have a private email set.", employee.name) if self.mail_to == "private" else _("%s does not have a work email set.", employee.name)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': message_display,
                        'sticky': False,
                        'type': 'danger',
                    }
                }
            partner_by_employee[employee] = self.env['mail.thread']._mail_find_partner_from_emails([email_used], records=self, force_create=True)[0]


        sign_request = self.env['sign.request']
        if not self.browse().has_access('create'):
            sign_request = sign_request.sudo()

        sign_values = []
        sign_templates_employee_ids = self.sign_template_ids.filtered(lambda t: len(t.sign_item_ids.mapped('responsible_id')) == 1)
        sign_templates_both_ids = self.sign_template_ids - sign_templates_employee_ids
        for employee in self.employee_ids:
            for sign_template_id in sign_templates_employee_ids:
                sign_values.append((
                    sign_template_id, employee,
                    [{'role_id': self.employee_role_id.id,
                    'partner_id': partner_by_employee[employee].id}]
                ))
            for sign_template_id in sign_templates_both_ids:
                second_role = sign_template_id.sign_item_ids.responsible_id - self.employee_role_id
                sign_values.append((
                    sign_template_id, employee,
                    [{'role_id': self.employee_role_id.id,
                    'partner_id': partner_by_employee[employee].id},
                    {'role_id': second_role.id,
                    'partner_id': self.responsible_id.partner_id.id}]
                ))

        sign_requests = self.env['sign.request'].create([{
            'template_id': sign_request_values[0].id,
            'request_item_ids': [Command.create({
                'partner_id': signer['partner_id'],
                'role_id': signer['role_id'],
            }) for signer in sign_request_values[2]],
            'reference': sign_request_values[0].name,
            'subject': self.subject,
            'message': self.message,
            'attachment_ids': [(4, attachment.copy().id) for attachment in self.attachment_ids], # Attachments may not be bound to multiple sign requests
        } for sign_request_values in sign_values])
        sign_requests.message_subscribe(partner_ids=self.cc_partner_ids.ids)

        if not self.browse().has_access('write'):
            sign_requests = sign_requests.sudo()

        for sign_request, sign_value in zip(sign_requests, sign_values):
            sign_request.toggle_favorited()
            employee = sign_value[1]
            if self.contract_id.employee_id == employee:
                self.contract_id.sign_request_ids += sign_request
            else:
                employee.sign_request_ids += sign_request

        for employee in self.employee_ids:
            if self.responsible_id and sign_templates_both_ids:
                signatories_text = _('%(employee)s and %(responsible)s are the signatories.', employee=employee.display_name, responsible=self.responsible_id.display_name)
            else:
                signatories_text = _('Only %s has to sign.', employee.display_name)
            record_to_post = self.contract_id if self.contract_id.employee_id == employee else employee
            record_to_post.message_post(
                body=(
                    _('%(user_name)s requested a new signature on the following documents:') + Markup('<br/><ul>%(documents)s</ul>%(signatories_text)s')
                ) % {
                    'user_name': self.env.user.display_name,
                    'documents': Markup('\n').join(Markup('<li>%s</li>') % name for name in self.sign_template_ids.mapped('name')),
                    'signatories_text': signatories_text
                }
            )

        if len(sign_requests) == 1 and ((self.env.user.id in self.employee_ids.user_id.ids) or (self.env.user.id == self.responsible_id.id and sign_templates_both_ids)):
            return sign_requests.go_to_document()
        return True
