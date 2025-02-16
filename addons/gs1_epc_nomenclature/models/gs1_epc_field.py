from odoo.addons.gs1_epc_nomenclature.models.gs1_epc_utils import extract_bits
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Gs1EpcField(models.TransientModel):
    _name = 'gs1.epc.field'
    _description = 'Electronic Product Code Field'
    _order = 'sequence asc, id desc'

    field_template_id = fields.Many2one(string='Field Template', comodel_name='gs1.epc.template.field', ondelete='cascade', required=True)
    name = fields.Char(related='field_template_id.name', readonly=True)
    bit_size = fields.Integer(string='Bit Size', required=True, store=True, readonly=False)  # Known at runtime in some cases : partition, ...
    char_size = fields.Integer(string='Character Size', default=0 , store=True)
    offset = fields.Integer(string='Offset')  # TODO : compute based on previous fields bit_size
    sequence = fields.Integer(string='Sequence', required=True, help='Used to order fields in the Scheme')
    raw_value = fields.Char(string='Raw Value', help='The raw value of the field represented as a string')  # TODO : Compute & inverse with value through encode/decode methods
    value = fields.Char(string='Value', help='The value of the field represented as a string')  # TODO : Getter : parse the value based on the encoding -> str, int, ...
    scheme_id = fields.Many2one(string='Scheme', comodel_name='gs1.epc.scheme', ondelete='cascade', required=True)
    encoding = fields.Selection(related='field_template_id.encoding', readonly=True)
    sub_encoding = fields.Selection(
        string='Sub Encoding Method', required=False, default='000', selection=[
            ('000', 'Variable-length integer'),
            ('001', 'Variable-length upper case hexadecimal'),
            ('010', 'Variable-length lower case hexadecimal'),
            ('011', 'Variable-length filesafe URI-safe base 64 (see RFC 4648 section 5)'),
            ('100', 'Variable-length 7-bit ASCII'),
            ('101', 'Variable-length URN Code 40'),
        ], help='Sub-Encoding/Decoding method used to parse the field.')
    partition_table = fields.Char(related='scheme_id.scheme_template_id.partition_table_name', readonly=True)

    def decode(self):
        previous_field = self._get_previous_field()
        if previous_field:
            self.offset = previous_field.offset + previous_field.bit_size
            self.raw_value = extract_bits(self.scheme_id.raw_value, self.bit_size, self.offset)
        # base on previous field, compute offset, length, and extract value from scheme.raw_value
        self.field_template_id.decode(self)

    def encode(self):
        self.field_template_id.encode(self)

    def _get_next_field(self, depth=1, strict=False):
        domain = [('scheme_id', '=', self.scheme_id.id), ('sequence', '>', self.sequence)]
        order = 'sequence asc'
        return self._get_neighbors(domain, order, depth, strict)

    def _get_previous_field(self, depth=1, strict=False):
        domain = [('scheme_id', '=', self.scheme_id.id), ('sequence', '<', self.sequence)]
        order = 'sequence desc'
        return self._get_neighbors(domain, order, depth, strict)

    def _get_neighbors(self, domain, order, depth, strict):
        fields = self.scheme_id.field_ids.search(domain, order=order, limit=depth)
        if strict and len(fields) != depth:
            raise UserError(_("There's not enough fields in the scheme."))
        return fields
