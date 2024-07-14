# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command


class HrRecruitmentSignDocumentWizard(models.TransientModel):
    _name = 'hr.recruitment.sign.document.wizard'
    _description = 'Sign document in recruitment'

    def _group_hr_contract_domain(self):
        group = self.env.ref('hr_contract.group_hr_contract_manager', raise_if_not_found=False)
        return [('groups_id', 'in', group.ids)] if group else []

    def _get_sign_template_ids(self):
        return self.env['sign.template'].search([])\
            .filtered(lambda t: 1 <= t.responsible_count <= 2)

    def _default_get_template_warning(self):
        return not bool(self._get_sign_template_ids()) and _('No appropriate template could be found, please make sure you configured them properly.')

    applicant_id = fields.Many2one('hr.applicant')
    partner_id = fields.Many2one(related='applicant_id.partner_id', store=True)
    partner_name = fields.Char(related='applicant_id.partner_name', readonly=True)
    applicant_role_id = fields.Many2one(
        "sign.item.role",
        string="Applicant Role", required=True,
        domain="[('id', 'in', sign_template_responsible_ids)]",
        compute='_compute_applicant_role_id', store=True, readonly=False,
        help="Applicant's role on the templates to sign. The same role must be present in all the templates")
    responsible_id = fields.Many2one(
        'res.users',
        string='Responsible', domain=_group_hr_contract_domain)
    sign_template_responsible_ids = fields.Many2many(
        'sign.item.role', compute='_compute_responsible_ids')
    possible_template_ids = fields.Many2many(
        'sign.template',
        compute='_compute_possible_template_ids')
    sign_template_ids = fields.Many2many(
        'sign.template', string='Documents to sign',
        domain="[('id', 'in', possible_template_ids)]",
        help="""Documents to sign. Only documents with 1 or 2 different responsible are selectable.
        Documents with 1 responsible will only have to be signed by the applicant while documents with 2 different responsible will have to be signed by both the applicant and the responsible.
        """, required=True)
    has_both_template = fields.Boolean(compute='_compute_has_both_template')
    template_warning = fields.Char(default=_default_get_template_warning, store=False)

    subject = fields.Char(string="Subject", required=True, default='Signature Request')
    message = fields.Html("Message")
    cc_partner_ids = fields.Many2many('res.partner', string="Copy to")
    attachment_ids = fields.Many2many('ir.attachment')

    @api.depends('sign_template_responsible_ids')
    def _compute_applicant_role_id(self):
        for wizard in self:
            if wizard.applicant_role_id not in wizard.sign_template_responsible_ids:
                wizard.applicant_role_id = False
            if len(wizard.sign_template_responsible_ids) == 1:
                wizard.applicant_role_id = wizard.sign_template_responsible_ids._origin

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

    @api.depends('sign_template_ids')
    def _compute_has_both_template(self):
        for wizard in self:
            wizard.has_both_template = bool(wizard.sign_template_ids.filtered(lambda t: len(t.sign_item_ids.mapped('responsible_id')) == 2))

    def validate_signature(self):
        self.ensure_one()

        sign_request = self.env['sign.request']
        if not self.check_access_rights('create', raise_exception=False):
            sign_request = sign_request.sudo()

        sign_values = []
        sign_templates_applicant_ids = self.sign_template_ids.filtered(lambda t: len(t.sign_item_ids.mapped('responsible_id')) == 1)
        sign_templates_both_ids = self.sign_template_ids - sign_templates_applicant_ids

        for sign_template_id in sign_templates_applicant_ids:
            sign_values.append((
                sign_template_id,
                [{
                    'role_id': self.applicant_role_id.id,
                    'partner_id': self.partner_id.id
                }]
            ))
        for sign_template_id in sign_templates_both_ids:
            second_role = sign_template_id.sign_item_ids.responsible_id - self.applicant_role_id
            sign_values.append((
                sign_template_id,
                [{
                    'role_id': self.applicant_role_id.id,
                    'partner_id': self.partner_id.id
                }, {
                    'role_id': second_role.id,
                    'partner_id': self.responsible_id.partner_id.id
                }]
            ))

        sign_requests = self.sudo().env['sign.request'].create([{
            'template_id': sign_request_values[0].id,
            'request_item_ids': [Command.create({
                'partner_id': signer['partner_id'],
                'role_id': signer['role_id'],
            }) for signer in sign_request_values[1]],
            'reference': _('Signature Request - %s', sign_request_values[0].name),
            'subject': self.subject,
            'message': self.message,
            'attachment_ids': [(4, attachment.copy().id) for attachment in self.attachment_ids], # Attachments may not be bound to multiple sign requests
        } for sign_request_values in sign_values])
        sign_requests.message_subscribe(partner_ids=self.cc_partner_ids.ids)

        if not self.check_access_rights('write', raise_exception=False):
            sign_requests = sign_requests.sudo()

        for sign_request in sign_requests:
            sign_request.toggle_favorited()

        if self.responsible_id and sign_templates_both_ids:
            signatories_text = _('%s and %s are the signatories.', self.partner_id.display_name, self.responsible_id.display_name)
        else:
            signatories_text = _('Only %s has to sign.', self.partner_id.display_name)
        record_to_post = self.applicant_id
        record_to_post.message_post_with_source(
            'hr_recruitment_sign.message_signature_request',
            render_values={
                'user_name': self.env.user.display_name,
                'document_names': self.sign_template_ids.mapped('name'),
                'signatories_text': signatories_text
            },
            subtype_xmlid='mail.mt_comment',
        )

        if len(sign_requests) == 1 and self.env.user.id == self.responsible_id.id:
            return sign_requests.go_to_document()
        return True
