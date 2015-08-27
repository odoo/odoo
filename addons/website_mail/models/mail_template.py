# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, models

class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.model
    def render_template(self, template_txt, model, res_ids, post_process=False):
        context = dict(self.env.context)
        website = self.env['website'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
        context.update({'website': website})
        return super(MailTemplate, self.with_context(context)).render_template(template_txt, model, res_ids, post_process=post_process)
