# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class SmsTemplate(models.Model):
    _inherit = 'sms.template'

    @api.model
<<<<<<< 18.0
    def _search_display_name(self, operator, value):
||||||| e4874075c478e9d5c36acc1105c7e33f4d738437
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
=======
    def _search(self, domain, *args, **kwargs):
>>>>>>> e0d7458f726a8394d75f19fd51a3dfe6c34aa8ac
        """Context-based hack to filter reference field in a m2o search box to emulate a domain the ORM currently does not support.

        As we can not specify a domain on a reference field, we added a context
        key `filter_template_on_event` on the template reference field. If this
<<<<<<< 18.0
        key is set, we add our domain in the `domain` in the `_search_display_name`
||||||| e4874075c478e9d5c36acc1105c7e33f4d738437
        key is set, we add our domain in the `domain` in the `_name_search`
=======
        key is set, we add our domain in the `domain` in the `_search`
>>>>>>> e0d7458f726a8394d75f19fd51a3dfe6c34aa8ac
        method to filtrate the SMS templates.
        """
        domain = super()._search_display_name(operator, value)
        if self.env.context.get('filter_template_on_event'):
            domain = expression.AND([[('model', '=', 'event.registration')], domain])
<<<<<<< 18.0
        return domain
||||||| e4874075c478e9d5c36acc1105c7e33f4d738437
        return super()._name_search(name, domain, operator, limit, order)
=======
        return super()._search(domain, *args, **kwargs)
>>>>>>> e0d7458f726a8394d75f19fd51a3dfe6c34aa8ac

    def unlink(self):
        res = super().unlink()
        domain = ('template_ref', 'in', [f"{template._name},{template.id}" for template in self])
        self.env['event.mail'].sudo().search([domain]).unlink()
        self.env['event.type.mail'].sudo().search([domain]).unlink()
        return res
