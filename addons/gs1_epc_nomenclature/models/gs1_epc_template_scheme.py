from odoo.addons.gs1_epc_nomenclature.models.gs1_epc_utils import get_uri_body_elements, get_uri_header, write_bits

from odoo import models, fields, _
from odoo.exceptions import UserError


class Gs1EpcTemplateScheme(models.Model):
    _name = 'gs1.epc.template.scheme'
    _description = 'Electronic Product Code Scheme Template'
    _order = 'id asc'

    name = fields.Char(string='Scheme Name', required=True, help='EPC Scheme Name')
    description = fields.Char(string='Scheme Description', required=True, help='EPC Scheme Description')
    header_value = fields.Integer(string='Header Value', required=True, help='EPC Header Value')  #TODO : Not NULL Index
    bit_size_min = fields.Integer(string='Minimal Size in Bits', required=True)
    bit_size_max = fields.Integer(string='Maximal Size in Bits', required=True)
    field_template_ids = fields.Many2many(string='Fields', comodel_name='gs1.epc.template.field', required=True)
    partition_table_name = fields.Char(string='Partition Table Name', required=False, help='Name of the Partition Table')
    uri_pattern_pure = fields.Char(string='Pure Identity URI Pattern', required=True, help='EPC Pure Identity URI Pattern')
    uri_pattern_tag = fields.Char(string='Tag URI Pattern', required=True, help='EPC Tag URI Pattern') #TODO : Not NULL Index
    aidc_available = fields.Boolean(string='Support AIDC Data', default=False)
    deprecated = fields.Boolean(string='Deprecated', default=False, help='This scheme has been deprecated. It is still possible to decode tag already using it but not to encode new tag with this scheme.')

    def _create_scheme_fields(self, scheme):
        field_values = [{
            'field_template_id': field_template.id,
            'sequence': seq + 1,
            'scheme_id': scheme.id,
            'bit_size': field_template.bit_size_max, #FIXME
        } for field_template, seq in zip(self.field_template_ids, range(len(self.field_template_ids)))]
        field_values[0]['raw_value'] = write_bits(self.header_value, field_values[0]['bit_size'])
        field_values[0]['value'] = get_uri_header(self.uri_pattern_tag)
        field_values[0]['bit_size'] = self.header_value.bit_length()  # May be less than 8 due to loss of leftmost '0' bit(s) from the EPC code
        field_ids = self.env['gs1.epc.field'].create(field_values)
        if scheme.uri_tag:
            mapped_uri = self.get_mapped_uri_data(scheme.uri_tag)
            for field in scheme.field_ids[1:]:
                if field.field_template_id.uri_portion in mapped_uri:
                    field.value = mapped_uri[field.field_template_id.uri_portion]
        if not scheme.uri_tag:
            scheme._compute_uri_tag() # FIXME LATER -___-" or Remove thos f*xsddvz computed field and explicitely assign them
        return field_ids

    def check_uri_tag(self, uri_tag):
        # TODO : extend verification => regex,...
        if len(get_uri_body_elements(self.uri_pattern_tag)) != len(get_uri_body_elements(uri_tag)):
            raise UserError(_('The URI Tag must have the same number of elements as the Scheme URI Tag.'))
            # CHECKME & FIXME : No more true for TDS > 2.0 EPC coding : uri replaced by GS1 digital link, + AIDC
        return True

    def get_mapped_uri_data(self, uri):
        return dict(zip(get_uri_body_elements(self.uri_pattern_tag), get_uri_body_elements(uri)))
