import re

from odoo.addons.gs1_epc_nomenclature.models.gs1_epc_utils import extract_bits, get_uri_body_elements

from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError


class Gs1EpcScheme(models.TransientModel):
    _name = 'gs1.epc.scheme'
    _description = 'Electronic Product Code Scheme'
    _order = 'id desc'

    scheme_template_id = fields.Many2one(string='Scheme Template', comodel_name='gs1.epc.template.scheme', ondelete='cascade', required=True)
    name = fields.Char(related='scheme_template_id.name', readonly=True)
    description = fields.Char(related='scheme_template_id.description', readonly=True)
    field_ids = fields.One2many(string='Fields', comodel_name='gs1.epc.field', inverse_name='scheme_id', required=True)
    aidc_enabled = fields.Boolean(string='+AIDC Toggle Bit', default=False)
    raw_value = fields.Integer(string='Raw Value', help='The raw value of the scheme', compute="_compute_raw_value", inverse="_set_raw_value")
    hex_value = fields.Char(string='Hex Value', help='The hex value of the scheme', compute="_compute_hex_value")
    uri_tag = fields.Char(string='Tag URI ', help='EPC Tag URI', compute="_compute_uri_tag", inverse="_set_uri_tag")

    @api.model_create_multi
    def create(self, vals_list):
        res = self.env['gs1.epc.scheme']
        for vals in vals_list:
            if 'raw_value' not in vals and 'uri_tag' not in vals:
                continue
            vals['scheme_template_id'] = self._get_scheme_template(vals).id
            # if 'raw_value' in vals:
                # shift_length = vals['raw_value'].bit_length() // 16 - self._missing_epc_bit(vals.raw_value.bit_length())
                # vals['raw_value'] = vals['raw_value'] >> shift_length

        res = super().create(vals_list)
        for scheme in res:
             scheme.field_ids = scheme.scheme_template_id._create_scheme_fields(scheme)
        return res

    def _get_scheme_template(self, vals):
        domain = self._get_scheme_template_domain(vals)
        scheme_template_id = self.env['gs1.epc.template.scheme'].search(domain, limit=1)
        if not scheme_template_id:
            raw_value = vals.get('raw_value')
            uri_tag = vals.get('uri_tag')
            if raw_value:
                raise UserError(_('Scheme Template not found for raw_value {raw_value}'))
            if uri_tag:
                raise UserError(_('Scheme Template not found for uri_tag {uri_tag}'))
        if self.uri_tag:
            scheme_template_id.check_uri_tag(self.uri_tag)
        return scheme_template_id

    def _get_scheme_template_domain(self, vals):
        if vals.get('raw_value'):
            value = vals.get('raw_value')
            header_length = self.env.ref('gs1_epc_nomenclature.gs1_epc_template_field_header').bit_size_min #FIXME
            header_value = extract_bits(value, header_length - (self._missing_epc_bit(value.bit_length()) % 8))
            return [('header_value', '=', header_value)]
        result = re.search(r'.*:', vals.get('uri_tag'))
        if result:
            tag_identifier = result.group(0)
        else:
            raise UserError(_("Uri Tag is not valid"))
        return [('uri_pattern_tag', '=ilike', tag_identifier + '%')]

    @api.depends('scheme_template_id', 'uri_tag')
    def _compute_raw_value(self):
        for scheme in self:
        # Encode uri_tag
            if scheme.raw_value or not scheme.field_ids or not scheme.scheme_template_id or not scheme.uri_tag:
                continue
            if scheme.scheme_template_id.deprecated:
                raise UserError(_('It is not possible to encode new tag with this scheme as it has been deprecated.'))  # FIXME : make non-blocking, Warn the user instead
            for field in scheme.field_ids[1:]:
                field.encode()
            total_size = scheme._normalize_epc_length(sum(len(field.raw_value) for field in scheme.field_ids))
            bit_string = ''.join(field.raw_value for field in scheme.field_ids).ljust(total_size, '0')  # Group raw_value of all fields ordered by sequence
            scheme.raw_value = int(bit_string, 2)

    @api.depends('raw_value')
    def _compute_hex_value(self):
        for scheme in self:
            if scheme.raw_value and scheme.raw_value != 0:
                scheme.hex_value = f"{scheme.raw_value:x}"

    @api.depends('scheme_template_id', 'raw_value')
    def _compute_uri_tag(self):
        # Decode raw_value
        for scheme in self:
            if scheme.uri_tag or not scheme.field_ids or not scheme.scheme_template_id or not scheme.raw_value:
                continue
            for field in scheme.field_ids[1:]:
                field.decode()

            uri_values = dict.fromkeys(get_uri_body_elements(scheme.scheme_template_id.uri_pattern_tag))
            for field in scheme.field_ids[1:]:
                key = field.field_template_id.uri_portion
                if key and key in uri_values:
                    uri_values[key] = field.value
            scheme.uri_tag = f"urn:epc:tag:{scheme.field_ids[0].value}:{'.'.join(uri_values.values())}"
            # print(scheme.uri_tag)

    def _set_raw_value(self):
        self.raw_value = self.raw_value

    def _set_uri_tag(self):
        self.uri_tag = self.uri_tag

    @classmethod
    def _normalize_epc_length(cls, raw_length):
        # EPC encoding must have a multiple of 16 bits.
        # c.f. [TDS  2.1], §15.1.1
        return raw_length + cls._missing_epc_bit(raw_length)

    @classmethod
    def _missing_epc_bit(cls, raw_length):
        remainder = raw_length % 16
        return (16 - remainder) if remainder else 0
