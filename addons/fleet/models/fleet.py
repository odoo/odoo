# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
import datetime
from dateutil.relativedelta import relativedelta

import openerp
from openerp import tools
from openerp.exceptions import UserError
from openerp.osv import fields, osv
from openerp.tools.translate import _

def str_to_datetime(strdate):
    return datetime.datetime.strptime(strdate, tools.DEFAULT_SERVER_DATE_FORMAT)

class fleet_vehicle_cost(osv.Model):
    _name = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle'
    _order = 'date desc, vehicle_id asc'

    def _get_odometer(self, cr, uid, ids, odometer_id, arg, context):
        res = dict.fromkeys(ids, False)
        for record in self.browse(cr,uid,ids,context=context):
            if record.odometer_id:
                res[record.id] = record.odometer_id.value
        return res

    def _set_odometer(self, cr, uid, id, name, value, args=None, context=None):
        if not value:
            raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
        date = self.browse(cr, uid, id, context=context).date
        if not(date):
            date = fields.date.context_today(self, cr, uid, context=context)
        vehicle_id = self.browse(cr, uid, id, context=context).vehicle_id
        data = {'value': value, 'date': date, 'vehicle_id': vehicle_id.id}
        odometer_id = self.pool.get('fleet.vehicle.odometer').create(cr, uid, data, context=context)
        return self.write(cr, uid, id, {'odometer_id': odometer_id}, context=context)

    _columns = {
        'name': fields.related('vehicle_id', 'name', type="char", string='Name', store=True),
        'vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle', required=True, help='Vehicle concerned by this log'),
        'cost_subtype_id': fields.many2one('fleet.service.type', 'Type', help='Cost type purchased with this cost'),
        'amount': fields.float('Total Price'),
        'cost_type': fields.selection([('contract', 'Contract'), ('services','Services'), ('fuel','Fuel'), ('other','Other')], 'Category of the cost', help='For internal purpose only', required=True),
        'parent_id': fields.many2one('fleet.vehicle.cost', 'Parent', help='Parent cost to this current cost'),
        'cost_ids': fields.one2many('fleet.vehicle.cost', 'parent_id', 'Included Services'),
        'odometer_id': fields.many2one('fleet.vehicle.odometer', 'Odometer', help='Odometer measure of the vehicle at the moment of this log'),
        'odometer': fields.function(_get_odometer, fnct_inv=_set_odometer, type='float', string='Odometer Value', help='Odometer measure of the vehicle at the moment of this log'),
        'odometer_unit': fields.related('vehicle_id', 'odometer_unit', type="char", string="Unit", readonly=True),
        'date' :fields.date('Date',help='Date when the cost has been executed'),
        'contract_id': fields.many2one('fleet.vehicle.log.contract', 'Contract', help='Contract attached to this cost'),
        'auto_generated': fields.boolean('Automatically Generated', readonly=True),
    }

    _defaults ={
        'cost_type': 'other',
    }

    def create(self, cr, uid, data, context=None):
        #make sure that the data are consistent with values of parent and contract records given
        if 'parent_id' in data and data['parent_id']:
            parent = self.browse(cr, uid, data['parent_id'], context=context)
            data['vehicle_id'] = parent.vehicle_id.id
            data['date'] = parent.date
            data['cost_type'] = parent.cost_type
        if 'contract_id' in data and data['contract_id']:
            contract = self.pool.get('fleet.vehicle.log.contract').browse(cr, uid, data['contract_id'], context=context)
            data['vehicle_id'] = contract.vehicle_id.id
            data['cost_subtype_id'] = contract.cost_subtype_id.id
            data['cost_type'] = contract.cost_type
        if 'odometer' in data and not data['odometer']:
            #if received value for odometer is 0, then remove it from the data as it would result to the creation of a
            #odometer log with 0, which is to be avoided
            del(data['odometer'])
        return super(fleet_vehicle_cost, self).create(cr, uid, data, context=context)


class fleet_vehicle_tag(osv.Model):
    _name = 'fleet.vehicle.tag'
    _columns = {
        'name': fields.char('Name', required=True),
        'color': fields.integer('Color Index'),
    }
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class fleet_vehicle_state(osv.Model):
    _name = 'fleet.vehicle.state'
    _order = 'sequence asc'
    _columns = {
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Sequence', help="Used to order the note stages")
    }
    _sql_constraints = [('fleet_state_name_unique','unique(name)', 'State name already exists')]



class fleet_vehicle_model(osv.Model):

    def name_get(self, cr, uid, ids, context=None):
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.name
            if record.brand_id.name:
                name = record.brand_id.name + '/' + name
            res.append((record.id, name))
        return res

    def on_change_brand(self, cr, uid, ids, model_id, context=None):
        if not model_id:
            return {'value': {'image_medium': False}}
        brand = self.pool.get('fleet.vehicle.model.brand').browse(cr, uid, model_id, context=context)
        return {
            'value': {
                'image_medium': brand.image,
            }
        }

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc'

    _columns = {
        'name': fields.char('Model name', required=True),
        'brand_id': fields.many2one('fleet.vehicle.model.brand', 'Make', required=True, help='Make of the vehicle'),
        'vendors': fields.many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors'),
        'image': fields.related('brand_id', 'image', type="binary", string="Logo"),
        'image_medium': fields.related('brand_id', 'image_medium', type="binary", string="Logo (medium)"),
        'image_small': fields.related('brand_id', 'image_small', type="binary", string="Logo (small)"),
    }


class fleet_vehicle_model_brand(osv.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand model of the vehicle'
    _order = 'name asc'

    name = openerp.fields.Char('Make', required=True)

    image = openerp.fields.Binary("Logo", attachment=True,
        help="This field holds the image used as logo for the brand, limited to 1024x1024px.")
    image_medium = openerp.fields.Binary("Medium-sized image",
        compute='_compute_images', inverse='_inverse_image_medium', store=True, attachment=True,
        help="Medium-sized logo of the brand. It is automatically "\
             "resized as a 128x128px image, with aspect ratio preserved. "\
             "Use this field in form views or some kanban views.")
    image_small = openerp.fields.Binary("Small-sized image",
        compute='_compute_images', inverse='_inverse_image_small', store=True, attachment=True,
        help="Small-sized logo of the brand. It is automatically "\
             "resized as a 64x64px image, with aspect ratio preserved. "\
             "Use this field anywhere a small image is required.")

    @openerp.api.depends('image')
    def _compute_images(self):
        for rec in self:
            rec.image_medium = tools.image_resize_image_medium(rec.image)
            rec.image_small = tools.image_resize_image_small(rec.image)

    def _inverse_image_medium(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_medium)

    def _inverse_image_small(self):
        for rec in self:
            rec.image = tools.image_resize_image_big(rec.image_small)


class fleet_vehicle(osv.Model):

    _inherit = 'mail.thread'

    def _vehicle_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = record.model_id.brand_id.name + '/' + record.model_id.name + '/' + record.license_plate
        return res

    def return_action_to_open(self, cr, uid, ids, context=None):
        """ This opens the xml view specified in xml_id for the current vehicle """
        if context is None:
            context = {}
        if context.get('xml_id'):
            res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet', context['xml_id'], context=context)
            res['context'] = context
            res['context'].update({'default_vehicle_id': ids[0]})
            res['domain'] = [('vehicle_id','=', ids[0])]
            return res
        return False

    def act_show_log_cost(self, cr, uid, ids, context=None):
        """ This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
            @return: the costs log view
        """
        if context is None:
            context = {}
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet','fleet_vehicle_costs_act', context=context)
        res['context'] = context
        res['context'].update({
            'default_vehicle_id': ids[0],
            'search_default_parent_false': True
        })
        res['domain'] = [('vehicle_id','=', ids[0])]
        return res

    def _get_odometer(self, cr, uid, ids, odometer_id, arg, context):
        res = dict.fromkeys(ids, 0)
        for record in self.browse(cr,uid,ids,context=context):
            ids = self.pool.get('fleet.vehicle.odometer').search(cr, uid, [('vehicle_id', '=', record.id)], limit=1, order='value desc')
            if len(ids) > 0:
                res[record.id] = self.pool.get('fleet.vehicle.odometer').browse(cr, uid, ids[0], context=context).value
        return res

    def _set_odometer(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            date = fields.date.context_today(self, cr, uid, context=context)
            data = {'value': value, 'date': date, 'vehicle_id': id}
            return self.pool.get('fleet.vehicle.odometer').create(cr, uid, data, context=context)

    def _search_get_overdue_contract_reminder(self, cr, uid, obj, name, args, context):
        res = []
        for field, operator, value in args:
            assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
            if (operator == '=' and value == True) or (operator in ('<>', '!=') and value == False):
                search_operator = 'in'
            else:
                search_operator = 'not in'
            today = fields.date.context_today(self, cr, uid, context=context)
            cr.execute('select cost.vehicle_id, count(contract.id) as contract_number FROM fleet_vehicle_cost cost left join fleet_vehicle_log_contract contract on contract.cost_id = cost.id WHERE contract.expiration_date is not null AND contract.expiration_date < %s AND contract.state IN (\'open\', \'toclose\') GROUP BY cost.vehicle_id', (today,))
            res_ids = [x[0] for x in cr.fetchall()]
            res.append(('id', search_operator, res_ids))
        return res

    def _search_contract_renewal_due_soon(self, cr, uid, obj, name, args, context):
        res = []
        for field, operator, value in args:
            assert operator in ('=', '!=', '<>') and value in (True, False), 'Operation not supported'
            if (operator == '=' and value == True) or (operator in ('<>', '!=') and value == False):
                search_operator = 'in'
            else:
                search_operator = 'not in'
            today = fields.date.context_today(self, cr, uid, context=context)
            datetime_today = datetime.datetime.strptime(today, tools.DEFAULT_SERVER_DATE_FORMAT)
            limit_date = str((datetime_today + relativedelta(days=+15)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT))
            cr.execute('select cost.vehicle_id, count(contract.id) as contract_number FROM fleet_vehicle_cost cost left join fleet_vehicle_log_contract contract on contract.cost_id = cost.id WHERE contract.expiration_date is not null AND contract.expiration_date > %s AND contract.expiration_date < %s AND contract.state IN (\'open\', \'toclose\') GROUP BY cost.vehicle_id', (today, limit_date))
            res_ids = [x[0] for x in cr.fetchall()]
            res.append(('id', search_operator, res_ids))
        return res

    def _get_contract_reminder_fnc(self, cr, uid, ids, field_names, unknow_none, context=None):
        res= {}
        for record in self.browse(cr, uid, ids, context=context):
            overdue = False
            due_soon = False
            total = 0
            name = ''
            for element in record.log_contracts:
                if element.state in ('open', 'toclose') and element.expiration_date:
                    current_date_str = fields.date.context_today(self, cr, uid, context=context)
                    due_time_str = element.expiration_date
                    current_date = str_to_datetime(current_date_str)
                    due_time = str_to_datetime(due_time_str)
                    diff_time = (due_time-current_date).days
                    if diff_time < 0:
                        overdue = True
                        total += 1
                    if diff_time < 15 and diff_time >= 0:
                            due_soon = True;
                            total += 1
                    if overdue or due_soon:
                        ids = self.pool.get('fleet.vehicle.log.contract').search(cr,uid,[('vehicle_id', '=', record.id), ('state', 'in', ('open', 'toclose'))], limit=1, order='expiration_date asc')
                        if len(ids) > 0:
                            #we display only the name of the oldest overdue/due soon contract
                            name=(self.pool.get('fleet.vehicle.log.contract').browse(cr, uid, ids[0], context=context).cost_subtype_id.name)

            res[record.id] = {
                'contract_renewal_overdue': overdue,
                'contract_renewal_due_soon': due_soon,
                'contract_renewal_total': (total - 1), #we remove 1 from the real total for display purposes
                'contract_renewal_name': name,
            }
        return res

    def _get_default_state(self, cr, uid, context):
        try:
            model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'fleet', 'vehicle_state_active')
        except ValueError:
            model_id = False
        return model_id
    
    def _count_all(self, cr, uid, ids, field_name, arg, context=None):
        Odometer = self.pool['fleet.vehicle.odometer']
        LogFuel = self.pool['fleet.vehicle.log.fuel']
        LogService = self.pool['fleet.vehicle.log.services']
        LogContract = self.pool['fleet.vehicle.log.contract']
        Cost = self.pool['fleet.vehicle.cost']
        return {
            vehicle_id: {
                'odometer_count': Odometer.search_count(cr, uid, [('vehicle_id', '=', vehicle_id)], context=context),
                'fuel_logs_count': LogFuel.search_count(cr, uid, [('vehicle_id', '=', vehicle_id)], context=context),
                'service_count': LogService.search_count(cr, uid, [('vehicle_id', '=', vehicle_id)], context=context),
                'contract_count': LogContract.search_count(cr, uid, [('vehicle_id', '=', vehicle_id)], context=context),
                'cost_count': Cost.search_count(cr, uid, [('vehicle_id', '=', vehicle_id), ('parent_id', '=', False)], context=context)
            }
            for vehicle_id in ids
        }

    _name = 'fleet.vehicle'
    _description = 'Information on a vehicle'
    _order= 'license_plate asc'
    _columns = {
        'name': fields.function(_vehicle_name_get_fnc, type="char", string='Name', store=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'license_plate': fields.char('License Plate', required=True, help='License plate number of the vehicle (ie: plate number for a car)'),
        'vin_sn': fields.char('Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)', copy=False),
        'driver_id': fields.many2one('res.partner', 'Driver', help='Driver of the vehicle'),
        'model_id': fields.many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle'),
        'log_fuel': fields.one2many('fleet.vehicle.log.fuel', 'vehicle_id', 'Fuel Logs'),
        'log_services': fields.one2many('fleet.vehicle.log.services', 'vehicle_id', 'Services Logs'),
        'log_contracts': fields.one2many('fleet.vehicle.log.contract', 'vehicle_id', 'Contracts'),
        'cost_count': fields.function(_count_all, type='integer', string="Costs" , multi=True),
        'contract_count': fields.function(_count_all, type='integer', string='Contracts', multi=True),
        'service_count': fields.function(_count_all, type='integer', string='Services', multi=True),
        'fuel_logs_count': fields.function(_count_all, type='integer', string='Fuel Logs', multi=True),
        'odometer_count': fields.function(_count_all, type='integer', string='Odometer', multi=True),
        'acquisition_date': fields.date('Acquisition Date', required=False, help='Date when the vehicle has been bought'),
        'color': fields.char('Color', help='Color of the vehicle'),
        'state_id': fields.many2one('fleet.vehicle.state', 'State', help='Current state of the vehicle', ondelete="set null"),
        'location': fields.char('Location', help='Location of the vehicle (garage, ...)'),
        'seats': fields.integer('Seats Number', help='Number of seats of the vehicle'),
        'doors': fields.integer('Doors Number', help='Number of doors of the vehicle'),
        'tag_ids' :fields.many2many('fleet.vehicle.tag', 'fleet_vehicle_vehicle_tag_rel', 'vehicle_tag_id','tag_id', 'Tags', copy=False),
        'odometer': fields.function(_get_odometer, fnct_inv=_set_odometer, type='float', string='Last Odometer', help='Odometer measure of the vehicle at the moment of this log'),
        'odometer_unit': fields.selection([('kilometers', 'Kilometers'),('miles','Miles')], 'Odometer Unit', help='Unit of the odometer ',required=True),
        'transmission': fields.selection([('manual', 'Manual'), ('automatic', 'Automatic')], 'Transmission', help='Transmission Used by the vehicle'),
        'fuel_type': fields.selection([('gasoline', 'Gasoline'), ('diesel', 'Diesel'), ('electric', 'Electric'), ('hybrid', 'Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle'),
        'horsepower': fields.integer('Horsepower'),
        'horsepower_tax': fields.float('Horsepower Taxation'),
        'power': fields.integer('Power', help='Power in kW of the vehicle'),
        'co2': fields.float('CO2 Emissions', help='CO2 emissions of the vehicle'),
        'image': fields.related('model_id', 'image', type="binary", string="Logo"),
        'image_medium': fields.related('model_id', 'image_medium', type="binary", string="Logo (medium)"),
        'image_small': fields.related('model_id', 'image_small', type="binary", string="Logo (small)"),
        'contract_renewal_due_soon': fields.function(_get_contract_reminder_fnc, fnct_search=_search_contract_renewal_due_soon, type="boolean", string='Has Contracts to renew', multi='contract_info'),
        'contract_renewal_overdue': fields.function(_get_contract_reminder_fnc, fnct_search=_search_get_overdue_contract_reminder, type="boolean", string='Has Contracts Overdue', multi='contract_info'),
        'contract_renewal_name': fields.function(_get_contract_reminder_fnc, type="text", string='Name of contract to renew soon', multi='contract_info'),
        'contract_renewal_total': fields.function(_get_contract_reminder_fnc, type="integer", string='Total of contracts due or overdue minus one', multi='contract_info'),
        'car_value': fields.float('Car Value', help='Value of the bought vehicle'),
        }

    _defaults = {
        'doors': 5,
        'odometer_unit': 'kilometers',
        'state_id': _get_default_state,
    }

    def on_change_model(self, cr, uid, ids, model_id, context=None):
        if not model_id:
            return {}
        model = self.pool.get('fleet.vehicle.model').browse(cr, uid, model_id, context=context)
        return {
            'value': {
                'image_medium': model.image,
            }
        }

    def create(self, cr, uid, data, context=None):
        context = dict(context or {}, mail_create_nolog=True)
        vehicle_id = super(fleet_vehicle, self).create(cr, uid, data, context=context)
        vehicle = self.browse(cr, uid, vehicle_id, context=context)
        self.message_post(cr, uid, [vehicle_id], body=_('%s %s has been added to the fleet!') % (vehicle.model_id.name,vehicle.license_plate), context=context)
        return vehicle_id

    def write(self, cr, uid, ids, vals, context=None):
        """
        This function write an entry in the openchatter whenever we change important information
        on the vehicle like the model, the drive, the state of the vehicle or its license plate
        """
        for vehicle in self.browse(cr, uid, ids, context):
            changes = []
            if 'model_id' in vals and vehicle.model_id.id != vals['model_id']:
                value = self.pool.get('fleet.vehicle.model').browse(cr,uid,vals['model_id'],context=context).name
                oldmodel = vehicle.model_id.name or _('None')
                changes.append(_("Model: from '%s' to '%s'") %(oldmodel, value))
            if 'driver_id' in vals and vehicle.driver_id.id != vals['driver_id']:
                value = self.pool.get('res.partner').browse(cr,uid,vals['driver_id'],context=context).name
                olddriver = (vehicle.driver_id.name) or _('None')
                changes.append(_("Driver: from '%s' to '%s'") %(olddriver, value))
            if 'state_id' in vals and vehicle.state_id.id != vals['state_id']:
                value = self.pool.get('fleet.vehicle.state').browse(cr,uid,vals['state_id'],context=context).name
                oldstate = vehicle.state_id.name or _('None')
                changes.append(_("State: from '%s' to '%s'") %(oldstate, value))
            if 'license_plate' in vals and vehicle.license_plate != vals['license_plate']:
                old_license_plate = vehicle.license_plate or _('None')
                changes.append(_("License Plate: from '%s' to '%s'") %(old_license_plate, vals['license_plate']))

            if len(changes) > 0:
                self.message_post(cr, uid, [vehicle.id], body=", ".join(changes), context=context)

        vehicle_id = super(fleet_vehicle,self).write(cr, uid, ids, vals, context)
        return True


class fleet_vehicle_odometer(osv.Model):
    _name='fleet.vehicle.odometer'
    _description='Odometer log for a vehicle'
    _order='date desc'

    def _vehicle_log_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            name = record.vehicle_id.name
            if not name:
                name = record.date
            elif record.date:
                name += ' / '+ record.date
            res[record.id] = name
        return res

    def on_change_vehicle(self, cr, uid, ids, vehicle_id, context=None):
        if not vehicle_id:
            return {}
        odometer_unit = self.pool.get('fleet.vehicle').browse(cr, uid, vehicle_id, context=context).odometer_unit
        return {
            'value': {
                'unit': odometer_unit,
            }
        }

    _columns = {
        'name': fields.function(_vehicle_log_name_get_fnc, type="char", string='Name', store=True),
        'date': fields.date('Date'),
        'value': fields.float('Odometer Value', group_operator="max"),
        'vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle', required=True),
        'unit': fields.related('vehicle_id', 'odometer_unit', type="char", string="Unit", readonly=True),
    }
    _defaults = {
        'date': fields.date.context_today,
    }


class fleet_vehicle_log_fuel(osv.Model):

    def on_change_vehicle(self, cr, uid, ids, vehicle_id, context=None):
        if not vehicle_id:
            return {}
        vehicle = self.pool.get('fleet.vehicle').browse(cr, uid, vehicle_id, context=context)
        odometer_unit = vehicle.odometer_unit
        driver = vehicle.driver_id.id
        return {
            'value': {
                'odometer_unit': odometer_unit,
                'purchaser_id': driver,
            }
        }

    def on_change_liter(self, cr, uid, ids, liter, price_per_liter, amount, context=None):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        liter = float(liter)
        price_per_liter = float(price_per_liter)
        amount = float(amount)
        if liter > 0 and price_per_liter > 0 and round(liter*price_per_liter,2) != amount:
            return {'value' : {'amount' : round(liter * price_per_liter,2),}}
        elif amount > 0 and liter > 0 and round(amount/liter,2) != price_per_liter:
            return {'value' : {'price_per_liter' : round(amount / liter,2),}}
        elif amount > 0 and price_per_liter > 0 and round(amount/price_per_liter,2) != liter:
            return {'value' : {'liter' : round(amount / price_per_liter,2),}}
        else :
            return {}

    def on_change_price_per_liter(self, cr, uid, ids, liter, price_per_liter, amount, context=None):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        liter = float(liter)
        price_per_liter = float(price_per_liter)
        amount = float(amount)
        if liter > 0 and price_per_liter > 0 and round(liter*price_per_liter,2) != amount:
            return {'value' : {'amount' : round(liter * price_per_liter,2),}}
        elif amount > 0 and price_per_liter > 0 and round(amount/price_per_liter,2) != liter:
            return {'value' : {'liter' : round(amount / price_per_liter,2),}}
        elif amount > 0 and liter > 0 and round(amount/liter,2) != price_per_liter:
            return {'value' : {'price_per_liter' : round(amount / liter,2),}}
        else :
            return {}

    def on_change_amount(self, cr, uid, ids, liter, price_per_liter, amount, context=None):
        #need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        #make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        #liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        #of 3.0/2=1.5)
        #If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        #onchange. And in order to verify that there is no change in the result, we have to limit the precision of the 
        #computation to 2 decimal
        liter = float(liter)
        price_per_liter = float(price_per_liter)
        amount = float(amount)
        if amount > 0 and liter > 0 and round(amount/liter,2) != price_per_liter:
            return {'value': {'price_per_liter': round(amount / liter,2),}}
        elif amount > 0 and price_per_liter > 0 and round(amount/price_per_liter,2) != liter:
            return {'value': {'liter': round(amount / price_per_liter,2),}}
        elif liter > 0 and price_per_liter > 0 and round(liter*price_per_liter,2) != amount:
            return {'value': {'amount': round(liter * price_per_liter,2),}}
        else :
            return {}

    def _get_default_service_type(self, cr, uid, context):
        try:
            model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'fleet', 'type_service_refueling')
        except ValueError:
            model_id = False
        return model_id

    _name = 'fleet.vehicle.log.fuel'
    _description = 'Fuel log for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    _columns = {
        'liter': fields.float('Liter'),
        'price_per_liter': fields.float('Price Per Liter'),
        'purchaser_id': fields.many2one('res.partner', 'Purchaser', domain="['|',('customer','=',True),('employee','=',True)]"),
        'inv_ref': fields.char('Invoice Reference', size=64),
        'vendor_id': fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]"),
        'notes': fields.text('Notes'),
        'cost_id': fields.many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade'),
        'cost_amount': fields.related('cost_id', 'amount', string='Amount', type='float', store=True), #we need to keep this field as a related with store=True because the graph view doesn't support (1) to address fields from inherited table and (2) fields that aren't stored in database
    }
    _defaults = {
        'date': fields.date.context_today,
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'fuel',
    }


class fleet_vehicle_log_services(osv.Model):

    def on_change_vehicle(self, cr, uid, ids, vehicle_id, context=None):
        if not vehicle_id:
            return {}
        vehicle = self.pool.get('fleet.vehicle').browse(cr, uid, vehicle_id, context=context)
        odometer_unit = vehicle.odometer_unit
        driver = vehicle.driver_id.id
        return {
            'value': {
                'odometer_unit': odometer_unit,
                'purchaser_id': driver,
            }
        }

    def _get_default_service_type(self, cr, uid, context):
        try:
            model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'fleet', 'type_service_service_8')
        except ValueError:
            model_id = False
        return model_id

    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _name = 'fleet.vehicle.log.services'
    _description = 'Services for vehicles'
    _columns = {
        'purchaser_id': fields.many2one('res.partner', 'Purchaser', domain="['|',('customer','=',True),('employee','=',True)]"),
        'inv_ref': fields.char('Invoice Reference'),
        'vendor_id': fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]"),
        'cost_amount': fields.related('cost_id', 'amount', string='Amount', type='float', store=True), #we need to keep this field as a related with store=True because the graph view doesn't support (1) to address fields from inherited table and (2) fields that aren't stored in database
        'notes': fields.text('Notes'),
        'cost_id': fields.many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade'),
    }
    _defaults = {
        'date': fields.date.context_today,
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'services'
    }


class fleet_service_type(osv.Model):
    _name = 'fleet.service.type'
    _description = 'Type of services available on a vehicle'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'category': fields.selection([('contract', 'Contract'), ('service', 'Service'), ('both', 'Both')], 'Category', required=True, help='Choose wheter the service refer to contracts, vehicle services or both'),
    }


class fleet_vehicle_log_contract(osv.Model):

    def scheduler_manage_auto_costs(self, cr, uid, context=None):
        #This method is called by a cron task
        #It creates costs for contracts having the "recurring cost" field setted, depending on their frequency
        #For example, if a contract has a reccuring cost of 200 with a weekly frequency, this method creates a cost of 200 on the first day of each week, from the date of the last recurring costs in the database to today
        #If the contract has not yet any recurring costs in the database, the method generates the recurring costs from the start_date to today
        #The created costs are associated to a contract thanks to the many2one field contract_id
        #If the contract has no start_date, no cost will be created, even if the contract has recurring costs
        vehicle_cost_obj = self.pool.get('fleet.vehicle.cost')
        d = datetime.datetime.strptime(fields.date.context_today(self, cr, uid, context=context), tools.DEFAULT_SERVER_DATE_FORMAT).date()
        contract_ids = self.pool.get('fleet.vehicle.log.contract').search(cr, uid, [('state','!=','closed')], offset=0, limit=None, order=None,context=None, count=False)
        deltas = {'yearly': relativedelta(years=+1), 'monthly': relativedelta(months=+1), 'weekly': relativedelta(weeks=+1), 'daily': relativedelta(days=+1)}
        for contract in self.pool.get('fleet.vehicle.log.contract').browse(cr, uid, contract_ids, context=context):
            if not contract.start_date or contract.cost_frequency == 'no':
                continue
            found = False
            last_cost_date = contract.start_date
            if contract.generated_cost_ids:
                last_autogenerated_cost_id = vehicle_cost_obj.search(cr, uid, ['&', ('contract_id','=',contract.id), ('auto_generated','=',True)], offset=0, limit=1, order='date desc',context=context, count=False)
                if last_autogenerated_cost_id:
                    found = True
                    last_cost_date = vehicle_cost_obj.browse(cr, uid, last_autogenerated_cost_id[0], context=context).date
            startdate = datetime.datetime.strptime(last_cost_date, tools.DEFAULT_SERVER_DATE_FORMAT).date()
            if found:
                startdate += deltas.get(contract.cost_frequency)
            while (startdate <= d) & (startdate <= datetime.datetime.strptime(contract.expiration_date, tools.DEFAULT_SERVER_DATE_FORMAT).date()):
                data = {
                    'amount': contract.cost_generated,
                    'date': startdate.strftime(tools.DEFAULT_SERVER_DATE_FORMAT),
                    'vehicle_id': contract.vehicle_id.id,
                    'cost_subtype_id': contract.cost_subtype_id.id,
                    'contract_id': contract.id,
                    'auto_generated': True
                }
                cost_id = self.pool.get('fleet.vehicle.cost').create(cr, uid, data, context=context)
                startdate += deltas.get(contract.cost_frequency)
        return True

    def scheduler_manage_contract_expiration(self, cr, uid, context=None):
        #This method is called by a cron task
        #It manages the state of a contract, possibly by posting a message on the vehicle concerned and updating its status
        datetime_today = datetime.datetime.strptime(fields.date.context_today(self, cr, uid, context=context), tools.DEFAULT_SERVER_DATE_FORMAT)
        limit_date = (datetime_today + relativedelta(days=+15)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        ids = self.search(cr, uid, ['&', ('state', '=', 'open'), ('expiration_date', '<', limit_date)], offset=0, limit=None, order=None, context=context, count=False)
        res = {}
        for contract in self.browse(cr, uid, ids, context=context):
            if contract.vehicle_id.id in res:
                res[contract.vehicle_id.id] += 1
            else:
                res[contract.vehicle_id.id] = 1

        for vehicle, value in res.items():
            self.pool.get('fleet.vehicle').message_post(cr, uid, vehicle, body=_('%s contract(s) need(s) to be renewed and/or closed!') % (str(value)), context=context)
        return self.write(cr, uid, ids, {'state': 'toclose'}, context=context)

    def run_scheduler(self, cr, uid, context=None):
        self.scheduler_manage_auto_costs(cr, uid, context=context)
        self.scheduler_manage_contract_expiration(cr, uid, context=context)
        return True

    def _vehicle_contract_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            name = record.vehicle_id.name
            if record.cost_subtype_id.name:
                name += ' / '+ record.cost_subtype_id.name
            if record.date:
                name += ' / '+ record.date
            res[record.id] = name
        return res

    def on_change_vehicle(self, cr, uid, ids, vehicle_id, context=None):
        if not vehicle_id:
            return {}
        odometer_unit = self.pool.get('fleet.vehicle').browse(cr, uid, vehicle_id, context=context).odometer_unit
        return {
            'value': {
                'odometer_unit': odometer_unit,
            }
        }

    def compute_next_year_date(self, strdate):
        oneyear = datetime.timedelta(days=365)
        curdate = str_to_datetime(strdate)
        return datetime.datetime.strftime(curdate + oneyear, tools.DEFAULT_SERVER_DATE_FORMAT)

    def on_change_start_date(self, cr, uid, ids, strdate, enddate, context=None):
        if (strdate):
            return {'value': {'expiration_date': self.compute_next_year_date(strdate),}}
        return {}

    def get_days_left(self, cr, uid, ids, prop, unknow_none, context=None):
        """return a dict with as value for each contract an integer
        if contract is in an open state and is overdue, return 0
        if contract is in a closed state, return -1
        otherwise return the number of days before the contract expires
        """
        res = {}
        for record in self.browse(cr, uid, ids, context=context):
            if (record.expiration_date and (record.state == 'open' or record.state == 'toclose')):
                today = str_to_datetime(time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT))
                renew_date = str_to_datetime(record.expiration_date)
                diff_time = (renew_date-today).days
                res[record.id] = diff_time > 0 and diff_time or 0
            else:
                res[record.id] = -1
        return res

    def act_renew_contract(self, cr, uid, ids, context=None):
        assert len(ids) == 1, "This operation should only be done for 1 single contract at a time, as it it suppose to open a window as result"
        for element in self.browse(cr, uid, ids, context=context):
            #compute end date
            startdate = str_to_datetime(element.start_date)
            enddate = str_to_datetime(element.expiration_date)
            diffdate = (enddate - startdate)
            default = {
                'date': fields.date.context_today(self, cr, uid, context=context),
                'start_date': datetime.datetime.strftime(str_to_datetime(element.expiration_date) + datetime.timedelta(days=1), tools.DEFAULT_SERVER_DATE_FORMAT),
                'expiration_date': datetime.datetime.strftime(enddate + diffdate, tools.DEFAULT_SERVER_DATE_FORMAT),
            }
            newid = super(fleet_vehicle_log_contract, self).copy(cr, uid, element.id, default, context=context)
        mod, modid = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'fleet', 'fleet_vehicle_log_contract_form')
        return {
            'name':_("Renew Contract"),
            'view_mode': 'form',
            'view_id': modid,
            'view_type': 'tree,form',
            'res_model': 'fleet.vehicle.log.contract',
            'type': 'ir.actions.act_window',
            'domain': '[]',
            'res_id': newid,
            'context': {'active_id':newid}, 
        }

    def _get_default_contract_type(self, cr, uid, context=None):
        try:
            model, model_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'fleet', 'type_contract_leasing')
        except ValueError:
            model_id = False
        return model_id

    def on_change_indic_cost(self, cr, uid, ids, cost_ids, context=None):
        totalsum = 0.0
        for element in cost_ids:
            if element and len(element) == 3 and isinstance(element[2], dict):
                totalsum += element[2].get('amount', 0.0)
        return {
            'value': {
                'sum_cost': totalsum,
            }
        }

    def _get_sum_cost(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for contract in self.browse(cr, uid, ids, context=context):
            totalsum = 0
            for cost in contract.cost_ids:
                totalsum += cost.amount
            res[contract.id] = totalsum
        return res

    _inherits = {'fleet.vehicle.cost': 'cost_id'}
    _name = 'fleet.vehicle.log.contract'
    _description = 'Contract information on a vehicle'
    _order='state desc,expiration_date'
    _columns = {
        'name': fields.function(_vehicle_contract_name_get_fnc, type="text", string='Name', store=True),
        'start_date': fields.date('Contract Start Date', help='Date when the coverage of the contract begins'),
        'expiration_date': fields.date('Contract Expiration Date', help='Date when the coverage of the contract expirates (by default, one year after begin date)'),
        'days_left': fields.function(get_days_left, type='integer', string='Warning Date'),
        'insurer_id' :fields.many2one('res.partner', 'Vendor'),
        'purchaser_id': fields.many2one('res.partner', 'Contractor', help='Person to which the contract is signed for'),
        'ins_ref': fields.char('Contract Reference', size=64, copy=False),
        'state': fields.selection([('open', 'In Progress'), ('toclose','To Close'), ('closed', 'Terminated')],
                                  'Status', readonly=True, help='Choose wheter the contract is still valid or not',
                                  copy=False),
        'notes': fields.text('Terms and Conditions', help='Write here all supplementary informations relative to this contract', copy=False),
        'cost_generated': fields.float('Recurring Cost Amount', help="Costs paid at regular intervals, depending on the cost frequency. If the cost frequency is set to unique, the cost will be logged at the start date"),
        'cost_frequency': fields.selection([('no','No'), ('daily', 'Daily'), ('weekly','Weekly'), ('monthly','Monthly'), ('yearly','Yearly')], 'Recurring Cost Frequency', help='Frequency of the recuring cost', required=True),
        'generated_cost_ids': fields.one2many('fleet.vehicle.cost', 'contract_id', 'Generated Costs'),
        'sum_cost': fields.function(_get_sum_cost, type='float', string='Indicative Costs Total'),
        'cost_id': fields.many2one('fleet.vehicle.cost', 'Cost', required=True, ondelete='cascade'),
        'cost_amount': fields.related('cost_id', 'amount', string='Amount', type='float', store=True), #we need to keep this field as a related with store=True because the graph view doesn't support (1) to address fields from inherited table and (2) fields that aren't stored in database
    }
    _defaults = {
        'purchaser_id': lambda self, cr, uid, ctx: self.pool.get('res.users').browse(cr, uid, uid, context=ctx).partner_id.id or False,
        'date': fields.date.context_today,
        'start_date': fields.date.context_today,
        'state':'open',
        'expiration_date': lambda self, cr, uid, ctx: self.compute_next_year_date(fields.date.context_today(self, cr, uid, context=ctx)),
        'cost_frequency': 'no',
        'cost_subtype_id': _get_default_contract_type,
        'cost_type': 'contract',
    }

    def contract_close(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'closed'}, context=context)

    def contract_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

class fleet_contract_state(osv.Model):
    _name = 'fleet.contract.state'
    _description = 'Contains the different possible status of a leasing contract'

    _columns = {
        'name':fields.char('Contract Status', required=True),
    }
