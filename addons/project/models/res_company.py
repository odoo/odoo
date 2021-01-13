# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class Company(models.Model):
    _inherit = 'res.company'

    def _get_default_status_updates_template(self):
        return """
<p>
    <b>How is this project going?</b><br/><br/>
    <b>What have you achieved since the last update?</b><br/><br/>
    <b>What's blocking or slowing your progress?</b><br/><br/>
    <b>What are the next steps?</b><br/><br/>
</p>"""

    project_status_updates_template = fields.Html(default=_get_default_status_updates_template)
