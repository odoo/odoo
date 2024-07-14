# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class AvataxValidateAddress(models.TransientModel):
    _name = 'avatax.validate.address'
    _description = 'Suggests validated addresses from Avatax'

    partner_id = fields.Many2one('res.partner', required=True)

    street = fields.Char(related='partner_id.street', string="Street")
    street2 = fields.Char(related='partner_id.street2')
    zip = fields.Char(related='partner_id.zip', string="Zip Code")
    city = fields.Char(related='partner_id.city', string="City")
    state_id = fields.Many2one('res.country.state', related='partner_id.state_id', string="State")
    country_id = fields.Many2one('res.country', related='partner_id.country_id', string="Country")

    validated_street = fields.Char(compute='_compute_validated_address', string="Validated Street")
    validated_street2 = fields.Char(compute='_compute_validated_address')
    validated_zip = fields.Char(compute='_compute_validated_address', string="Validated Zip Code")
    validated_city = fields.Char(compute='_compute_validated_address', string="Validated City")
    validated_state_id = fields.Many2one('res.country.state', compute='_compute_validated_address', string="Validated State")
    validated_country_id = fields.Many2one('res.country', compute='_compute_validated_address', string="Validated Country")
    validated_latitude = fields.Float(compute='_compute_validated_address', string='Geo Latitude', digits=(10, 7))
    validated_longitude = fields.Float(compute='_compute_validated_address', string='Geo Longitude', digits=(10, 7))

    # field used to determine whether to allow updating the address or not
    is_already_valid = fields.Boolean(string="Is Already Valid", compute='_compute_validated_address')

    @api.depends('partner_id')
    def _compute_validated_address(self):
        for wizard in self:
            company = wizard.partner_id.company_id or wizard.env.company
            country = wizard.partner_id.country_id
            if country.code not in ('US', 'CA', False):
                raise ValidationError(_("Address validation is only supported for North American addresses."))

            client = self.env['account.external.tax.mixin']._get_client(company)
            response = client.resolve_address({
                'line1': wizard.street or '',
                'line2': wizard.street2 or '',
                'postalCode': wizard.zip or '',
                'city': wizard.city or '',
                'region': wizard.state_id.name or '',
                'country': country.code or '',
                'textCase': 'Mixed',
            })
            error = self.env['account.external.tax.mixin']._handle_response(response, _(
                "Odoo could not validate the address of %(partner)s with Avalara.",
                partner=wizard.partner_id.display_name,
            ))
            if error:
                raise ValidationError(error)
            if response.get('messages'):
                messages = response['messages']
                raise ValidationError('\n\n'.join(message['details'] for message in messages))
            if response.get('validatedAddresses'):
                validated = response['validatedAddresses'][0]
                wizard.validated_street = validated['line1']
                wizard.validated_street2 = validated['line2']
                wizard.validated_zip = validated['postalCode']
                wizard.validated_city = validated['city']
                wizard.validated_country_id = self.env['res.country'].search([
                    ('code', '=', validated['country'])]
                ).id
                wizard.validated_state_id = self.env['res.country.state'].search([
                    ('code', '=', validated['region']),
                    ('country_id', '=', wizard.validated_country_id.id),
                ]).id

                wizard.validated_latitude = validated.get('latitude')
                wizard.validated_longitude = validated.get('longitude')

                wizard.is_already_valid = (
                    wizard.street == wizard.validated_street
                    and wizard.street2 == wizard.validated_street2
                    and wizard.zip == wizard.validated_zip
                    and wizard.city == wizard.validated_city
                    and wizard.country_id == wizard.validated_country_id
                    and wizard.state_id == wizard.validated_state_id
                )

    def action_save_validated(self):
        for wizard in self:
            wizard.partner_id.write({
                'street': wizard.validated_street,
                'street2': wizard.validated_street2,
                'zip': wizard.validated_zip,
                'city': wizard.validated_city,
                'state_id': wizard.validated_state_id.id,
                'country_id': wizard.validated_country_id.id,
                'partner_latitude': wizard.validated_latitude,
                'partner_longitude': wizard.validated_longitude,
            })
        return True
