

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError
from datetime import datetime, date, timedelta

class account_intrastat_custom(models.Model):
    _name = 'account.intrastat.custom'
    _description = 'Account INTRASTAT - Customs'
    
    code = fields.Char(string='Code', size=6)
    name = fields.Char(string='Name')
    date_start = fields.Date(string='Date start')
    date_stop = fields.Date(string='Date stop')


class report_intrastat_code(models.Model):

    _inherit = 'report.intrastat.code'

    active = fields.Boolean(default=True)
    additional_unit_required = fields.Boolean(default=False,
        string='Unit of Measure Additional Required')
    additional_unit_from = fields.Selection(
        [('quantity', 'Quantity'),('weight', 'Weight'),('none', 'None')], 
        string='Additional Unit of Measure FROM')
    additional_unit_uom_id = fields.Many2one('product.uom', 
        string='Unit of Measure Additional')
    type = fields.Selection(
        [('good', 'Good'), ('service', 'Service')])
    description = fields.Char('Description', translate=True)
    
    
class res_country(models.Model):

    _inherit = 'res.country'
    
    @api.model
    def intrastat_validate(self):
        control_ISO_code = self._context.get('control_ISO_code', False)
        if not self:
            raise ValidationError(
                _('Missing Country' ))
        if control_ISO_code and not self.code:
            raise ValidationError(
                _('Country %s without ISO code') % (self.name,) )
        return True


class account_intrastat_transport(models.Model):
    _name = 'account.intrastat.transport'
    _description = 'Account INTRASTAT - Transport'
    
    code = fields.Char(string='Code', size=1, required=True)
    name = fields.Char(string='Name')


class account_intrastat_transation_nature(models.Model):
    _name = 'account.intrastat.transation.nature'
    _description = 'Account INTRASTAT - Transation Nature'
    
    code = fields.Char(string='Code', size=1, required=True)
    name = fields.Char(string='Name')

