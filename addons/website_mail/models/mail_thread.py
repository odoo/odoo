# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv, fields

# TODO for trunk, remove me
class MailThread(osv.AbstractModel):
    _inherit = 'mail.thread'

    _columns = {
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('message_type', '=', 'comment')
            ],
            string='Website Messages',
            help="Website communication history",
        ),
    }

    def template_footer(self):
        footer = super(MailThread, self).template_footer()
        website = self.env['website'].search([('company_id', '=', self.env.user.company_id.id)], limit=1)
        if website:
            if website.social_facebook:
                footer.append({'name': 'social_facebook', 'link': website.social_facebook})
            if website.social_twitter:
                footer.append({'name': 'social_twitter', 'link': website.social_twitter})
            if website.social_googleplus:
                footer.append({'name': 'social_googleplus', 'link': website.social_googleplus})
            if website.social_linkedin:
                footer.append({'name': 'social_linkedin', 'link': website.social_linkedin})
        return footer
