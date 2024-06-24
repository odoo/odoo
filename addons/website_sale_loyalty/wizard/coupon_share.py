# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class CouponShare(models.TransientModel):
    _name = 'coupon.share'
    _description = 'Create links that apply a coupon and redirect to a specific page'

    def _get_default_website_id(self):
        program_website_id = self.env['loyalty.program'].browse(self.env.context.get('default_program_id')).website_id
        if program_website_id:
            return program_website_id
        else:
            Website = self.env['website']
            websites = Website.search([])
            return len(websites) == 1 and websites or Website

    website_id = fields.Many2one('website', required=True, default=_get_default_website_id)
    coupon_id = fields.Many2one('loyalty.card', domain="[('program_id', '=', program_id)]")
    program_id = fields.Many2one('loyalty.program', required=True, domain=[
        '|', ('program_type', '=', 'coupons'), # All coupons programs
        '|', ('trigger', '=', 'with_code'), # All programs that require a code
             ('rule_ids.code', '!=', False), # All programs that can not trigger without a code
    ])
    program_website_id = fields.Many2one('website', string='Program Website', related='program_id.website_id')

    promo_code = fields.Char(compute='_compute_promo_code')
    share_link = fields.Char(compute='_compute_share_link')
    redirect = fields.Char(required=True, default='/shop')

    @api.constrains('coupon_id', 'program_id')
    def _check_program(self):
        if self.filtered(lambda record: not record.coupon_id and record.program_id.program_type == 'coupons'):
            raise ValidationError(_("A coupon is needed for coupon programs."))

    @api.constrains('website_id', 'program_id')
    def _check_website(self):
        if self.filtered(lambda record: record.program_website_id and record.program_website_id != record.website_id):
            raise ValidationError(_("The shared website should correspond to the website of the program."))

    @api.depends('coupon_id.code', 'program_id.rule_ids.code')
    def _compute_promo_code(self):
        for record in self:
            record.promo_code = record.coupon_id.code or record.program_id.rule_ids.filtered('code')[:1].code

    @api.depends('website_id', 'redirect')
    @api.depends_context('use_short_link')
    def _compute_share_link(self):
        for record in self:
            target_url = '{base}/coupon/{code}?{query}'.format(
                base=record.website_id.get_base_url(),
                code=record.promo_code,
                query=url_encode({'r': record.redirect}),
            )

            if record.env.context.get('use_short_link'):
                tracker = self.env['link.tracker'].search([('url', '=', target_url)], limit=1)
                if not tracker:
                    tracker = self.env['link.tracker'].create({'url': target_url})
                record.share_link = tracker.short_url
            else:
                record.share_link = target_url

    def action_generate_short_link(self):
        return {
            'name': _('Share'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'coupon.share',
            'target': 'new',
            'res_id': self.id,
            'context': {
                'use_short_link': True,
            }
        }

    @api.model
    def create_share_action(self, coupon=None, program=None):
        if bool(program) == bool(coupon):
            raise UserError(_("Provide either a coupon or a program."))

        return {
            'name': _('Share %s', self.env["loyalty.program"]._program_items_name().get((program or coupon).program_type, "")),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'coupon.share',
            'target': 'new',
            'context': {
                'default_program_id': program and program.id or coupon.program_id.id,
                'default_coupon_id': coupon and coupon.id or None,
            }
        }
