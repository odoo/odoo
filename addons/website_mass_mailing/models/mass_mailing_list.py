# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MassMailingList(models.Model):
    _inherit = 'mail.mass_mailing.list'

    def _default_popup_content(self):
        return """<div class="modal-header text-center">
    <h3 class="modal-title mt8">Odoo Presents</h3>
</div>
<div class="o_popup_message">
    <font>7</font>
    <strong>Business Hacks</strong>
    <span> to<br/>boost your marketing</span>
</div>
<p class="o_message_paragraph">Join our Marketing newsletter and get <strong>this white paper instantly</strong></p>"""

    popup_content = fields.Html(string="Website Popup Content", translate=True, sanitize_attributes=False,
                                default=_default_popup_content)
    popup_redirect_url = fields.Char(string="Website Popup Redirect URL", default='/')
