# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MassMailing(models.Model):
    _inherit = 'mail.mass_mailing'

    # mailing options
    mailing_type = fields.Selection(selection_add=[('sms', 'SMS')])
    # sms options
    body_plaintext = fields.Text('SMS Body')
    sms_template_id = fields.Many2one('sms.template', string='SMS Template', ondelete='set null')
    # opt_out_link

    @api.onchange('mailing_type')
    def _onchange_mailing_type(self):
        if self.mailing_type == 'sms' and not self.medium_id:
            self.medium_id = self.env.ref('mass_mailing_sms.utm_medium_sms').id

    @api.onchange('sms_template_id', 'mailing_type')
    def _onchange_sms_template_id(self):
        if self.mailing_type == 'sms' and self.sms_template_id:
            self.body_plaintext = self.sms_template_id.body

    def create(self, values):
        if values.get('mailing_type') == 'sms':
            if not values.get('medium_id'):
                values['medium_id'] = self.env.ref('mass_mailing_sms.utm_medium_sms').id
            if values.get('sms_template_id') and not values.get('body_plaintext'):
                values['body_plaintext'] = self.env['sms.template'].browse(values['sms_template_id']).body
        return super(MassMailing, self).create(values)

    def action_test_mailing(self):
        if self.mailing_type == 'sms':
            ctx = dict(self.env.context, default_mass_mailing_id=self.id)
            return {
                'name': _('Test Mailing'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mass.sms.test',
                'target': 'new',
                'context': ctx,
            }
        return super(MassMailing, self).action_test_mailing()

    def get_remaining_recipients(self):
        if self.mailing_type == 'sms':
            return self._sms_get_remaining_res_ids()
        return super(MassMailing, self).get_remaining_recipients()

    def _sms_get_remaining_res_ids(self):
        res_ids = self.get_recipients()  # TDE FIXME: already mailed ??
        done_res_ids = [r['res_id'] for r in self.env['sms.statistics'].sudo().search_read([
            ('res_model', '=', self.mailing_model_real),
            ('res_id', 'in', res_ids),
            ('mass_mailing_id', '=', self.id)], ['res_id'])]
        return [rid for rid in res_ids if rid not in done_res_ids]

    # def _get_opt_out_list(self):
    #     """Returns a set of emails opted-out in target model"""
    #     self.ensure_one()
    #     opt_out = {}
    #     target = self.env[self.mailing_model_real]
    #     if self.mailing_model_real == "mail.mass_mailing.contact":
    #         # if user is opt_out on One list but not on another
    #         # or if two user with same email address, one opted in and the other one opted out, send the mail anyway
    #         # TODO DBE Fixme : Optimise the following to get real opt_out and opt_in
    #         target_list_contacts = self.env['mail.mass_mailing.list_contact_rel'].search(
    #             [('list_id', 'in', self.contact_list_ids.ids)])
    #         opt_out_contacts = target_list_contacts.filtered(lambda rel: rel.opt_out).mapped('contact_id.email_normalized')
    #         opt_in_contacts = target_list_contacts.filtered(lambda rel: not rel.opt_out).mapped('contact_id.email_normalized')
    #         opt_out = set(c for c in opt_out_contacts if c not in opt_in_contacts)

    #         _logger.info(
    #             "Mass-mailing %s targets %s, blacklist: %s emails",
    #             self, target._name, len(opt_out))
    #     else:
    #         _logger.info("Mass-mailing %s targets %s, no opt out list available", self, target._name)
    #     return opt_out

    # def _get_seen_list(self):
    #     """Returns a set of emails already targeted by current mailing/campaign (no duplicates)"""
    #     self.ensure_one()
    #     target = self.env[self.mailing_model_real]

    #     # avoid loading a large number of records in memory
    #     # + use a basic heuristic for extracting emails
    #     query = """
    #         SELECT lower(substring(t.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
    #           FROM mail_mail_statistics s
    #           JOIN %(target)s t ON (s.res_id = t.id)
    #          WHERE substring(t.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
    #     """

    #     # Apply same 'get email field' rule from mail_thread.message_get_default_recipients
    #     if 'partner_id' in target._fields:
    #         mail_field = 'email'
    #         query = """
    #             SELECT lower(substring(p.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)'))
    #               FROM mail_mail_statistics s
    #               JOIN %(target)s t ON (s.res_id = t.id)
    #               JOIN res_partner p ON (t.partner_id = p.id)
    #              WHERE substring(p.%(mail_field)s, '([^ ,;<@]+@[^> ,;]+)') IS NOT NULL
    #         """
    #     elif issubclass(type(target), self.pool['mail.address.mixin']):
    #         mail_field = 'email_normalized'
    #     elif 'email_from' in target._fields:
    #         mail_field = 'email_from'
    #     elif 'partner_email' in target._fields:
    #         mail_field = 'partner_email'
    #     elif 'email' in target._fields:
    #         mail_field = 'email'
    #     else:
    #         raise UserError(_("Unsupported mass mailing model %s") % self.mailing_model_id.name)

    #     if self.mass_mailing_campaign_id.unique_ab_testing:
    #         query +="""
    #            AND s.mass_mailing_campaign_id = %%(mailing_campaign_id)s;
    #         """
    #     else:
    #         query +="""
    #            AND s.mass_mailing_id = %%(mailing_id)s
    #            AND s.model = %%(target_model)s;
    #         """
    #     query = query % {'target': target._table, 'mail_field': mail_field}
    #     params = {'mailing_id': self.id, 'mailing_campaign_id': self.mass_mailing_campaign_id.id, 'target_model': self.mailing_model_real}
    #     self._cr.execute(query, params)
    #     seen_list = set(m[0] for m in self._cr.fetchall())
    #     _logger.info(
    #         "Mass-mailing %s has already reached %s %s emails", self, len(seen_list), target._name)
    #     return seen_list

    # def _get_mass_mailing_context(self):
    #     """Returns extra context items with pre-filled blacklist and seen list for massmailing"""
    #     return {
    #         'mass_mailing_opt_out_list': self._get_opt_out_list(),
    #         'mass_mailing_seen_list': self._get_seen_list(),
    #         'post_convert_links': self._get_convert_links(),
    #     }

    def _send_sms_get_composer_values(self, res_ids):
        return {
            # content
            'body': self.body_plaintext,
            'template_id': self.sms_template_id.id,
            'res_model': self.mailing_model_real,
            'res_ids': repr(res_ids),
            # options
            'composition_mode': 'mass',
            'mass_mailing_id': self.id,
        }

    def send_mail(self, res_ids=None):
        mass_sms = self.filtered(lambda m: m.mailing_type == 'sms')
        if mass_sms:
            mass_sms.action_send_sms(res_ids=res_ids)
        return super(MassMailing, self - mass_sms).send_mail(res_ids=res_ids)

    def action_send_sms(self, res_ids=None):
        for mailing in self:
            if not res_ids:
                res_ids = mailing.get_remaining_recipients()
            if not res_ids:
                raise UserError(_('There is no recipients selected.'))

            composer = self.env['sms.composer'].create(mailing._send_sms_get_composer_values(res_ids))
            # extra_context = self._get_mass_mailing_context()

            # auto-commit except in testing mode
            # auto_commit = not getattr(threading.currentThread(), 'testing', False)
            # composer.send_mail(auto_commit=auto_commit)
            composer._action_send_sms()
            # mailing.write({'state': 'done', 'sent_date': fields.Datetime.now()})
        return True
