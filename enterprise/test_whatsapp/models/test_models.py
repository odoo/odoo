# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get


class WhatsAppTestBaseModel(models.Model):
    """ Base test model for whatsapp implementation, with mail thread support
    and number / partner. """
    _description = 'WhatsApp Base Test'
    _name = 'whatsapp.test.base'
    _inherit = [
        'mail.thread',
    ]

    name = fields.Char('Name')
    country_id = fields.Many2one('res.country', 'Country')
    customer_id = fields.Many2one('res.partner', 'Customer')
    guest_ids = fields.Many2many('res.partner')
    phone = fields.Char('Phone', compute='_compute_phone', readonly=False, store=True)
    user_id = fields.Many2one(comodel_name='res.users', string="Salesperson")
    datetime = fields.Datetime()
    selection_id = fields.Many2one('whatsapp.test.selection', 'Selection')
    selection_field = fields.Selection([
        ('selection_key_1', 'Selection Value 1'),
        ('selection_key_2', 'Selection Value 2'),
        ('selection_key_3', 'Selection Value 3'),
    ], string='Selection Field', default='selection_key_1')

    @api.depends('customer_id')
    def _compute_phone(self):
        for record in self.filtered(lambda rec: not rec.phone):
            record.phone = record.customer_id.phone

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['customer_id', 'guest_ids']

    def _wa_get_safe_phone_fields(self):
        return super()._wa_get_safe_phone_fields() + ['customer_id.phone', 'guest_ids.phone']


class WhatsAppTestNoThread(models.Model):
    """ Same as base test model but with no way to get a responsible. """
    _description = 'WhatsApp NoThread / NoResponsible'
    _name = 'whatsapp.test.nothread'

    name = fields.Char('Name')
    country_id = fields.Many2one('res.country', 'Country')
    customer_id = fields.Many2one('res.partner', 'Customer')
    phone = fields.Char('Phone', compute='_compute_phone', readonly=False, store=True)
    user_id = fields.Many2one('res.users', string="Salesperson")

    @api.depends('customer_id')
    def _compute_phone(self):
        for record in self.filtered(lambda rec: not rec.phone):
            record.phone = record.customer_id.phone


class WhatsAppTestNoThreadNoName(models.Model):
    """ Same as base test model but with no way to get a responsible and that
    does not have a name. """
    _description = 'WhatsApp NoThread / NoResponsible /NoName'
    _name = 'whatsapp.test.nothread.noname'
    _rec_name = 'customer_id'

    country_id = fields.Many2one('res.country', 'Country')
    customer_id = fields.Many2one('res.partner', 'Customer')
    phone = fields.Char('Phone', compute='_compute_phone', readonly=False, store=True)
    user_id = fields.Many2one('res.users', string="Salesperson")

    @api.depends('customer_id')
    def _compute_phone(self):
        for record in self.filtered(lambda rec: not rec.phone):
            record.phone = record.customer_id.phone


class WhatsAppTestResponsible(models.Model):
    """ Same as base test model but with responsible fields """
    _description = 'WhatsApp Responsible Test'
    _name = 'whatsapp.test.responsible'
    _inherit = [
        'whatsapp.test.base',
    ]

    user_ids = fields.Many2many('res.users', string="Salespersons")


class WhatsAppTestSelection(models.Model):
    """ Selection test model to test Selection fields using chain """
    _description = 'WhatsApp Selection Test'
    _name = 'whatsapp.test.selection'

    selection_field = fields.Selection([
        ('selection_key_4', 'Selection Value 4'),
        ('selection_key_5', 'Selection Value 5'),
        ('selection_key_6', 'Selection Value 6'),
    ], string='Selection Field', default='selection_key_4')


class WhatsAppTestTimezone(models.Model):
    """ Same as base test model but with timezone fields """
    _description = 'WhatsApp Timezone Test'
    _name = 'whatsapp.test.timezone'
    _inherit = [
        'whatsapp.test.base',
    ]

    tz = fields.Selection(_tz_get, string='Timezone')
