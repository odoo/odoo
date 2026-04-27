# Part of Odoo. See LICENSE file for full copyright and licensing details.

from urllib.parse import urlparse

from odoo import api, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError, ValidationError


class WhatsAppTemplateButton(models.Model):
    _name = 'whatsapp.template.button'
    _description = 'WhatsApp Template Button'
    _order = 'sequence,id'

    sequence = fields.Integer()
    name = fields.Char(string="Button Text", size=25)
    wa_template_id = fields.Many2one(comodel_name='whatsapp.template', required=True, ondelete='cascade')

    button_type = fields.Selection([
        ('url', 'Visit Website'),
        ('phone_number', 'Call Number'),
        ('quick_reply', 'Quick Reply')], string="Type", required=True, default='quick_reply')
    url_type = fields.Selection([
        ('static', 'Static'),
        ('dynamic', 'Dynamic')], string="Url Type", default='static')
    website_url = fields.Char(string="Website URL")
    call_number = fields.Char(string="Call Number")
    has_invalid_number = fields.Boolean(compute="_compute_has_invalid_number")
    variable_ids = fields.One2many(
        'whatsapp.template.variable', 'button_id',
        compute='_compute_variable_ids', precompute=True, store=True,
        copy=True)

    _sql_constraints = [
        (
            'unique_name_per_template',
            'UNIQUE(name, wa_template_id)',
            "Button names must be unique in a given template"
        )
    ]

    @api.depends('button_type', 'call_number')
    def _compute_has_invalid_number(self):
        for button in self:
            if button.button_type == 'phone_number' and button.call_number:
                try:
                    phone_validation.phone_format(
                        button.call_number,
                        False,
                        False,
                    )
                except UserError:
                    if country := self.env.user.country_id or self.env.company.country_id:
                        try:
                            phone_validation.phone_format(
                                button.call_number,
                                country.code,
                                country.phone_code,
                            )
                        except UserError:
                            button.has_invalid_number = True
                            continue
            button.has_invalid_number = False

    def _get_button_variable_vals(self, button):
        return {
            "demo_value": button.website_url + "???",
            "line_type": "button",
            "name": button.name,
            "wa_template_id": button.wa_template_id.id,
        }

    def _filter_dynamic_buttons(self):
        """
        Retrieve buttons filtered by 'dynamic' URL type.
        """
        dynamic_urls = self.filtered(lambda button: button.button_type == 'url' and button.url_type == 'dynamic')
        return dynamic_urls

    @api.depends('button_type', 'url_type', 'website_url', 'name')
    def _compute_variable_ids(self):
        button_urls = self._filter_dynamic_buttons()
        to_clear = self - button_urls
        for button in button_urls:
            if button.variable_ids:
                button.variable_ids = [
                    (1, button.variable_ids[0].id, self._get_button_variable_vals(button)),
                ]
            else:
                button.variable_ids = [
                    (0, 0, self._get_button_variable_vals(button)),
                ]
        if to_clear:
            to_clear.variable_ids = [(5, 0)]

    def check_variable_ids(self):
        for button in self:
            if len(button.variable_ids) > 1:
                raise ValidationError(_('Buttons may only contain one placeholder.'))
            if button.variable_ids and button.url_type != 'dynamic':
                raise ValidationError(_('Only dynamic urls may have a placeholder.'))
            elif button.url_type == 'dynamic' and not button.variable_ids:
                raise ValidationError(_('All dynamic urls must have a placeholder.'))
            if button.variable_ids.name != "{{1}}":
                raise ValidationError(_('The placeholder for a button can only be {{1}}.'))

    @api.onchange('website_url')
    def _onchange_website_url(self):
        if self.website_url:
            parsed_url = urlparse(self.website_url)
            if not (parsed_url.scheme in {'http', 'https'} and parsed_url.netloc):
                self.website_url = f"https://{self.website_url}"
