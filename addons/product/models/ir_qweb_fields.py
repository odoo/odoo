# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.tools.float_utils import float_get_decimals

import logging
_logger = logging.getLogger(__name__)


class WeightConverter(models.AbstractModel):
    """ ``weight`` converter, transforms a float field stored in the DB's
    default weight UoM (kg) to the chosen UoM.
    By default, the chosen UoM is the one set in the General Settings unless
    one is specified in the options under "weight_uom".

    E.g.: <span t-field="record.weight"
                t-options="{'widget': 'weight', 'weight_uom': record.weight_uom_id}"/>

    The weight value will be converted using the UoM factor and rounding and
    the html value will also display the UoM's name.
    """
    _name = 'ir.qweb.field.weight'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        formatted_amount = "%.{0}f".format(options['rounding']) % value
        return u'<span class="oe_weight_value">{0}\N{NO-BREAK SPACE}</span>{uom}'.format(formatted_amount, uom=options['name'])

    @api.model
    def record_to_html(self, record, field_name, options):
        options = dict(options)

        weight_uom = self.env['product.uom'].browse(int(self.env['ir.config_parameter'].sudo().get_param('database_weight_uom_id')))
        if options.get('weight_uom'):
            if not options.get('weight_uom').category_id or options.get('weight_uom').category_id.id != self.env.ref('product.product_uom_categ_kgm').id:
                _logger.error(_('Attempted to use Qweb weight widget with wrong UoM category. Falling back to defaults.'))
            else:
                weight_uom = options.get('weight_uom')

        options.update({'name': weight_uom.name, 'rounding': float_get_decimals(weight_uom.rounding)})
        value = record[field_name] * weight_uom.factor

        return self.value_to_html(value, options)


class VolumeConverter(models.AbstractModel):
    """ ``volume`` converter, transforms a float field stored in the DB's
    default volume UoM (kg) to the chosen UoM.
    By default, the chosen UoM is the one set in the General Settings unless
    one is specified in the options under "volume_uom".

    E.g.: <span t-field="record.volume"
                t-options="{'widget': 'volume', 'volume_uom': record.volume_uom_id}"/>

    The volume value will be converted using the UoM factor and rounding and
    the html value will also display the UoM's name.
    """
    _name = 'ir.qweb.field.volume'
    _inherit = 'ir.qweb.field'

    @api.model
    def value_to_html(self, value, options):
        formatted_amount = "%.{0}f".format(options['rounding']) % value
        return u'<span class="oe_volume_value">{0}\N{NO-BREAK SPACE}</span>{uom}'.format(formatted_amount, uom=options['name'])

    @api.model
    def record_to_html(self, record, field_name, options):
        options = dict(options)

        volume_uom = self.env['product.uom'].browse(int(self.env['ir.config_parameter'].sudo().get_param('database_volume_uom_id')))
        if options.get('volume_uom'):
            if not options.get('volume_uom').category_id or options.get('volume_uom').category_id.id != self.env.ref('product.product_uom_categ_vol').id:
                _logger.error(_('Attempted to use Qweb volume widget with wrong UoM category. Falling back to defaults.'))
            else:
                volume_uom = options.get('volume_uom')

        options.update({'name': volume_uom.name, 'rounding': float_get_decimals(volume_uom.rounding)})
        value = record[field_name] * volume_uom.factor

        return self.value_to_html(value, options)
