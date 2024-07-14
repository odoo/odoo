# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Company(models.Model):
    _inherit = 'res.company'

    sign_terms = fields.Html(string='Sign Default Terms and Conditions', translate=True,
        default="""<h1 style="text-align: center; ">Terms &amp; Conditions</h1>
        <p>Your conditions...</p>""")
    sign_terms_type = fields.Selection([('plain', 'Terms in Email'), ('html', 'Terms as Web Page')],
        default='plain', string='Sign Terms & Conditions format', help="""Terms in Email - The text will be displayed at the bottom of every signature request email.\n
        Terms as Web Page - A link will be pasted at the bottom of every signature request email, leading to your content.
        """)
    sign_terms_html = fields.Html(string='Sign Default Terms and Conditions as a Web page', translate=True,
        default="""<h1 style="text-align: center; ">Terms &amp; Conditions</h1>
        <p>Your conditions...</p>""", sanitize_attributes=False)
