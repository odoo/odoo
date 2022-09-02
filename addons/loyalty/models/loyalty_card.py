# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class LoyaltyCard(models.Model):
    _name = 'loyalty.card'
    _inherit = ['mail.thread']
    _description = 'Loyalty Coupon'
    _rec_name = 'code'

    @api.model
    def _generate_code(self):
        """
        Barcode identifiable codes.
        """
        return '044' + str(uuid4())[4:-8][3:]

    def name_get(self):
        return [(card.id, f'{card.program_id.name}: {card.code}') for card in self]

    program_id = fields.Many2one('loyalty.program', ondelete='restrict')
    company_id = fields.Many2one(related='program_id.company_id', store=True)
    currency_id = fields.Many2one(related='program_id.currency_id')
    # Reserved for this partner if non-empty
    partner_id = fields.Many2one('res.partner', index=True)
    points = fields.Float(tracking=True)
    point_name = fields.Char(related='program_id.portal_point_name', readonly=True)

    code = fields.Char(default=lambda self: self._generate_code(), required=True, readonly=True, index=True)
    expiration_date = fields.Date()

    use_count = fields.Integer(compute='_compute_use_count')

    _sql_constraints = [
        ('card_code_unique', 'UNIQUE(code)', 'A coupon/loyalty card must have a unique code.')
    ]

    @api.constrains('code')
    def _contrains_code(self):
        # Prevent a coupon from having the same code a program
        if self.env['loyalty.rule'].search_count([('mode', '=', 'with_code'), ('code', 'in', self.mapped('code'))]):
            raise ValidationError(_('A trigger with the same code as one of your coupon already exists.'))

    # Meant to be overriden
    def _compute_use_count(self):
        self.use_count = 0

    def _get_default_template(self):
        self.ensure_one()
        return self.program_id.communication_plan_ids.filtered(lambda m: m.trigger == 'create').mail_template_id[:1]

    def _get_mail_partner(self):
        self.ensure_one()
        return self.partner_id

    def _get_signature(self):
        """To be overriden"""
        self.ensure_one()
        return None

    def action_coupon_send(self):
        """ Open a window to compose an email, with the default template returned by `_get_default_template`
            message loaded by default
        """
        self.ensure_one()
        default_template = self._get_default_template()
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        ctx = dict(
            default_model='loyalty.card',
            default_res_id=self.id,
            default_use_template=bool(default_template),
            default_template_id=default_template and default_template.id,
            default_composition_mode='comment',
            default_email_layout_xmlid='mail.mail_notification_light',
            mark_coupon_as_sent=True,
            force_email=True,
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _send_creation_communication(self):
        """
        Sends the 'At Creation' communication plan if it exist for the given coupons.
        """
        if self.env.context.get('loyalty_no_mail', False) or self.env.context.get('action_no_send_mail', False):
            return
        # Ideally one per program, but multiple is supported
        create_comm_per_program = dict()
        for program in self.program_id:
            create_comm_per_program[program] = program.communication_plan_ids.filtered(lambda c: c.trigger == 'create')
        for coupon in self:
            if not create_comm_per_program[coupon.program_id] or not coupon._get_mail_partner():
                continue
            for comm in create_comm_per_program[coupon.program_id]:
                comm.mail_template_id.send_mail(res_id=coupon.id, email_layout_xmlid='mail.mail_notification_light')

    def _send_points_reach_communication(self, points_changes):
        """
        Send the 'When Reaching' communicaton plans for the given coupons.

        If a coupons passes multiple milestones we will only send the one with the highest target.
        """
        if self.env.context.get('loyalty_no_mail', False):
            return
        milestones_per_program = dict()
        for program in self.program_id:
            milestones_per_program[program] = program.communication_plan_ids\
                .filtered(lambda c: c.trigger == 'points_reach')\
                .sorted('points', reverse=True)
        for coupon in self:
            if not coupon._get_mail_partner():
                continue
            coupon_change = points_changes[coupon]
            # Do nothing if coupon lost points or did not change
            if not milestones_per_program[coupon.program_id] or\
                not coupon.partner_id or\
                coupon_change['old'] >= coupon_change['new']:
                continue
            this_milestone = False
            for milestone in milestones_per_program[coupon.program_id]:
                if coupon_change['old'] < milestone.points and milestone.points <= coupon_change['new']:
                    this_milestone = milestone
                    break
            if not this_milestone:
                continue
            this_milestone.mail_template_id.send_mail(res_id=coupon.id, email_layout_xmlid='mail.mail_notification_light')


    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        res._send_creation_communication()
        return res

    def write(self, vals):
        if not self.env.context.get('loyalty_no_mail', False) and 'points' in vals:
            points_before = {coupon: coupon.points for coupon in self}
        res = super().write(vals)
        if not self.env.context.get('loyalty_no_mail', False) and 'points' in vals:
            points_changes = {coupon: {'old': points_before[coupon], 'new': coupon.points} for coupon in self}
            self._send_points_reach_communication(points_changes)
        return res
