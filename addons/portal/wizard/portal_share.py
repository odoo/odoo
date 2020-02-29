# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class PortalShare(models.TransientModel):
    _name = 'portal.share'
    _description = 'Portal Sharing'

    @api.model
    def default_get(self, fields):
        result = super(PortalShare, self).default_get(fields)
        result['res_model'] = self._context.get('active_model', False)
        result['res_id'] = self._context.get('active_id', False)
        if result['res_model'] and result['res_id']:
            record = self.env[result['res_model']].browse(result['res_id'])
            result['share_link'] = record.get_base_url() + record._get_share_url(redirect=True)
        return result

    res_model = fields.Char('Related Document Model', required=True)
    res_id = fields.Integer('Related Document ID', required=True)
    partner_ids = fields.Many2many('res.partner', string="Recipients", required=True)
    note = fields.Text(help="Add extra content to display in the email")
    share_link = fields.Char(string="Link", compute='_compute_share_link')
    access_warning = fields.Text("Access warning", compute="_compute_access_warning")

    @api.depends('res_model', 'res_id')
    def _compute_share_link(self):
        for rec in self:
            rec.share_link = False
            if rec.res_model:
                res_model = self.env[rec.res_model]
                if isinstance(res_model, self.pool['portal.mixin']) and rec.res_id:
                    record = res_model.browse(rec.res_id)
                    rec.share_link = record.get_base_url() + record._get_share_url(redirect=True)

    @api.depends('res_model', 'res_id')
    def _compute_access_warning(self):
        for rec in self:
            rec.access_warning = False
            if rec.res_model:
                res_model = self.env[rec.res_model]
                if isinstance(res_model, self.pool['portal.mixin']) and rec.res_id:
                    record = res_model.browse(rec.res_id)
                    rec.access_warning = record.access_warning

    def action_send_mail(self):
        active_record = self.env[self.res_model].browse(self.res_id)
        template = self.env.ref('portal.portal_share_template', False)
        note = self.env.ref('mail.mt_note')
        signup_enabled = self.env['ir.config_parameter'].sudo().get_param('auth_signup.invitation_scope') == 'b2c'

        if hasattr(active_record, 'access_token') and active_record.access_token or not signup_enabled:
            partner_ids = self.partner_ids
        else:
            partner_ids = self.partner_ids.filtered(lambda x: x.user_ids)
        # if partner already user or record has access token send common link in batch to all user
        for partner in self.partner_ids:
            share_link = active_record.get_base_url() + active_record._get_share_url(redirect=True, pid=partner.id)
            active_record.with_context(mail_post_autofollow=True).message_post_with_view(template,
                values={'partner': partner, 'note': self.note, 'record': active_record,
                        'share_link': share_link},
                subject=_("You are invited to access %s" % active_record.display_name),
                subtype_id=note.id,
                email_layout_xmlid='mail.mail_notification_light',
                partner_ids=[(6, 0, partner.ids)])
        # when partner not user send individual mail with signup token
        for partner in self.partner_ids - partner_ids:
            #  prepare partner for signup and send singup url with redirect url
            partner.signup_get_auth_param()
            share_link = partner._get_signup_url_for_action(action='/mail/view', res_id=self.res_id, model=self.model)[partner.id]
            active_record.with_context(mail_post_autofollow=True).message_post_with_view(template,
                values={'partner': partner, 'note': self.note, 'record': active_record,
                        'share_link': share_link},
                subject=_("You are invited to access %s" % active_record.display_name),
                subtype_id=note.id,
                email_layout_xmlid='mail.mail_notification_light',
                partner_ids=[(6, 0, partner.ids)])
        return {'type': 'ir.actions.act_window_close'}
