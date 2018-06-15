# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class MailInviteShare(models.TransientModel):
    _name = 'mail.invite.share'

    @api.model
    def default_get(self, fields):
        result = super(MailInviteShare, self).default_get(fields)
        result['model'] = self._context.get('active_model')
        result['res_id'] = self._context.get('active_id')
        return result

    model = fields.Char('Related Document Model', required=True)
    res_id = fields.Integer('Related Document ID', required=True)
    partner_ids = fields.Many2many('res.partner', string="Recipients", required=True)
    note = fields.Text(help="Add extra content to display in the email")
    share_link = fields.Char(string="Document link", compute='_compute_share_link')
    share_warning = fields.Text("Share Warning", compute="_compute_share_link")

    @api.depends('model', 'res_id')
    def _compute_share_link(self):
        signup_enabled = self.env['ir.config_parameter'].sudo().get_param('auth_signup.invitation_scope') == 'b2c'
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            model = self.env[rec.model]
            if isinstance(model, self.pool['portal.mixin']):
                record = model.browse(rec.res_id)
                warning = record.share_warning
                if not hasattr(record, 'access_token') and not signup_enabled:
                    warning += _("Your current 'Customer Account' setting is set on 'B2B'. Therefore, the recipient won't be able to signup to view this document. Please create a portal user manually.\n")
                rec.share_warning = warning
                rec.share_link = base_url + record.get_share_url()

    @api.multi
    def send_mail_action(self):
        active_record = self.env[self.model].browse(self.res_id)
        template = self.env.ref('portal.portal_share_template', False)
        note = self.env.ref('mail.mt_note')
        signup_enabled = self.env['ir.config_parameter'].sudo().get_param('auth_signup.invitation_scope') == 'b2c'

        if hasattr(active_record, 'access_token') and active_record.access_token or not signup_enabled:
            partner_ids = self.partner_ids
        else:
            partner_ids = self.partner_ids.filtered(lambda x: x.user_ids)
        # if partner already user or record has access token send common link in batch to all user
        if partner_ids:
            active_record.with_context(mail_post_autofollow=True).message_post_with_view(template,
                values={'note': self.note, 'record': active_record, 'share_link': self.share_link},
                subject=_(active_record.display_name),
                subtype_id=note.id,
                partner_ids=[(6, 0, partner_ids.ids)])
        # when partner not user send invidual mail with signup token
        for partner in self.partner_ids - partner_ids:
            #  prepare partner for signup and send singup url with redirect url
            partner.signup_get_auth_param()
            share_link = partner._get_signup_url_for_action(action='/mail/view', res_id=self.res_id, model=self.model)[partner.id]
            active_record.with_context(mail_post_autofollow=True).message_post_with_view(template,
                values={'note': self.note, 'record': active_record, 'share_link': share_link},
                subject=_(active_record.display_name),
                subtype_id=note.id,
                partner_ids=[(6, 0, partner.ids)])
        return {'type': 'ir.actions.act_window_close'}
