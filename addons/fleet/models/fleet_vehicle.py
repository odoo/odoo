# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
import datetime
from openerp import tools
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta


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
        'contract_renewal_overdue': fields.function(_get_contract_reminder_fnc, fnct_search=_search_get_overdue_contract_reminder, type="boolean", string='Has Contracts Overdued', multi='contract_info'),
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
