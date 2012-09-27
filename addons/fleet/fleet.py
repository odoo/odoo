from itertools import chain
from osv import osv, fields
import time

class fleet_vehicle_model_type(osv.Model):
    _name = 'fleet.vehicle.type'
    _description = 'Type of the vehicle'
    _columns = {
        'name' : fields.char('Name', size=32, required=True),
    }

class fleet_vehicle_tag(osv.Model):
    _name = 'fleet.vehicle.tag'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

class fleet_vehicle_state(osv.Model):
    _name = 'fleet.vehicle.state'
    _columns = {
        'name': fields.char('Name', required=True),
        'sequence': fields.integer('Order',help="Used to order the note stages")
    }
    _order = 'sequence asc'

class fleet_vehicle_model(osv.Model):

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            name = record.modelname
            if record.brand.name:
                name = record.brand.name+' / '+name
            res.append((record.id, name))
        return res

    def _model_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'

    _columns = {
        'name' : fields.function(_model_name_get_fnc, type="char", string='Name', store=True),
        'modelname' : fields.char('Model name', size=32, required=True), 
        'brand' : fields.many2one('fleet.vehicle.model.brand', 'Model brand', required=True, help='Brand of the vehicle'),
        'vendors': fields.many2many('res.partner','fleet_vehicle_model_vendors','model_id', 'partner_id',string='Vendors',required=False),
        'image': fields.related('brand','image',type="binary",string="Logo",store=False)
    }

class fleet_vehicle_model_brand(osv.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand model of the vehicle'
    _columns = {
        'name' : fields.char('Brand Name',size=32, required=True),
        'image': fields.binary("Logo",help="This field holds the image used as logo for the brand, limited to 128x128px."),
    }

class fleet_vehicle(osv.Model):

    _inherit = 'mail.thread'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            if record.license_plate:
                name = record.license_plate
            if record.model_id.modelname:
                name = record.model_id.modelname + ' / ' + name
            if record.model_id.brand.name:
                name = record.model_id.brand.name+' / '+ name
            res.append((record.id, name))
        return res

    def _vehicle_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    def act_show_log_services(self, cr, uid, ids, context=None):
        """ This opens log view to view and add new log for this vehicle
            @return: the service log view
        """
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet','act_show_log_services', context)
        res['context'] = {
            'default_vehicle_id': ids[0]
        }
        res['domain']=[('vehicle_id','=', ids[0])]
        return res

    def act_show_log_fuel(self, cr, uid, ids, context=None):
        """ This opens log view to view and add new log for this vehicle
            @return: the service log view
        """
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet','act_show_log_fuel', context)
        res['context'] = {
            'default_vehicle_id': ids[0]
        }
        res['domain']=[('vehicle_id','=', ids[0])]
        return res    

    _name = 'fleet.vehicle'
    _description = 'Fleet Vehicle'

    _columns = {
        'name' : fields.function(_vehicle_name_get_fnc, type="char", string='Name', store=True),
        'company_id': fields.many2one('res.company', 'Company'),
        'license_plate' : fields.char('License plate', size=32, required=True, help='License plate number of the vehicle (ie: plate number for a car)'),
        'vin_sn' : fields.char('Chassis Number', size=32, required=False, help='Unique number written on the vehicle motor (VIN/SN number)'),
        'driver' : fields.many2one('res.partner', 'Driver',required=False, help='Driver of the vehicle'),
        'model_id' : fields.many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle'),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'vehicle_id', 'Other Logs'),
        'log_fuel' : fields.one2many('fleet.vehicle.log.fuel','vehicle_id', 'Fuel Logs'),
        'log_services' : fields.one2many('fleet.vehicle.log.services','vehicle_id', 'Services Logs'),
        'log_insurances' : fields.one2many('fleet.vehicle.log.insurance','vehicle_id', 'Insurances'),
        'acquisition_date' : fields.date('Acquisition date', required=False, help='Date when the vehicle has been bought'),
        'acquisition_price' : fields.integer('Price', help='Price of the bought vehicle'),
        'color' : fields.char('Color',size=32, help='Color of the vehicle'),
        'state': fields.many2one('fleet.vehicle.state', 'State', help='Current state of the vehicle', domain='[]'),
        'location' : fields.char('Location',size=32, help='Location of the vehicle (garage, ...)'),
        'doors' : fields.integer('Number of doors', help='Number of doors of the vehicle'),
        'tag_ids' :fields.many2many('fleet.vehicle.tag','vehicle_vehicle_tag_rel','vehicle_tag_id','tag_id','Tags'),

        'transmission' : fields.selection([('manual', 'Manual'),('automatic','Automatic')], 'Transmission', help='Transmission Used by the vehicle',required=False),
        'fuel_type' : fields.selection([('gasoline', 'Gasoline'),('diesel','Diesel'),('electric','Electric'),('hybrid','Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle',required=False),
        'horsepower' : fields.integer('Horsepower',required=False),
        'horsepower_tax': fields.float('Horsepower Taxation'),
        'power' : fields.integer('Power (kW)',required=False,help='Power in kW of the vehicle'),
        'co2' : fields.float('CO2 Emissions',required=False,help='CO2 emissions of the vehicle'),

        'image': fields.related('model_id','image',type="binary",string="Logo",store=False)
    }
    _defaults = {
        'doors' : 5,
    }

    def on_change_model(self, cr, uid, ids, model_id, context=None):
        # print "ids: %r" % (ids,)
        # print "model_id: %r" % (model_id,)
        # print "context: %r" % (context,)
        # import logging
        # logger = logging.getLogger('fleet.vehicle')
        # logger.info('Hello')

        # import ipdb
        # ipdb.set_trace()

        if not model_id:
            return {}

        model = self.pool.get('fleet.vehicle.model').browse(cr, uid, model_id, context=context)

        print "model: %r" % (model.name,)

        return {
            'value' : {
                'message' : "You have selected this %s model" % (model.name,),
            }
        }
    def create(self, cr, uid, data, context=None):
        vehicle_id = super(fleet_vehicle, self).create(cr, uid, data, context=context)
        try:
            vehicle = self.browse(cr, uid, vehicle_id, context=context)
            self.message_post(cr, uid, [vehicle_id], body='Vehicle %s has been added to the fleet!' % (vehicle.license_plate), context=context)
        except:
            pass # group deleted: do not push a message
        return vehicle_id

    def write(self, cr, uid, ids, vals, context=None):
        vehicle_id = super(fleet_vehicle,self).write(cr, uid, ids, vals, context)
        try:
            changes = {}
            for key,value in vals.items():
                if key == 'license_plate' or key == 'driver':
                    changes[key] = value
            if len(changes) > 0:
                self.message_post(cr, uid, [vehicle_id], body='Vehicle edited. Changes : '+ str(changes), context=context)
                #self.message_post(cr, uid, [vehicle_id], body='Vehicle edited. Changes : '+ ','.join(chain(*str(changes.items()))), context=context)
        except Exception as e:
            print e
            pass
        return vehicle_id

class fleet_vehicle_odometer(osv.Model):
    _name='fleet.vehicle.odometer'
    _description='Odometer log for a vehicle'

    _columns = {
        'name' : fields.char('Name',size=64),

        'date' : fields.date('Date'),
        'value' : fields.float('Odometer Value'),
        'unit' : fields.selection([('kilometers', 'Kilometers'),('miles','Miles')], 'Odometer Unit', help='Unit of the measurement',required=False),
        'vehicle_id' : fields.many2one('fleet.vehicle', 'Vehicle', required=True),
        'notes' : fields.text('Notes'),
    }
    _defaults = {
        'date' : time.strftime('%Y-%m-%d')
    }

class fleet_vehicle_log_fuel(osv.Model):

    _inherits = {'fleet.vehicle.odometer': 'odometer_id'}

    def on_change_liter(self, cr, uid, ids, liter, price_per_liter, amount, context=None):

        if liter > 0 and price_per_liter > 0:
            return {'value' : {'amount' : float(liter) * float(price_per_liter),}}
        elif liter > 0 and amount > 0:
            return {'value' : {'price_per_liter' : float(amount) / float(liter),}}
        elif price_per_liter > 0 and amount > 0:
            return {'value' : {'liter' : float(amount) / float(price_per_liter),}}
        else :
            return {}

    def on_change_price_per_liter(self, cr, uid, ids, liter, price_per_liter, amount, context=None):

        liter = float(liter);
        price_per_liter = float(price_per_liter);
        if price_per_liter > 0 and liter > 0:
            return {'value' : {'amount' : float(liter) * float(price_per_liter),}}
        elif price_per_liter > 0 and amount > 0:
            return {'value' : {'liter' : float(amount) / float(price_per_liter),}}
        elif liter > 0 and amount > 0:
            return {'value' : {'price_per_liter' : float(amount) / float(liter),}}
        else :
            return {}

    def on_change_amount(self, cr, uid, ids, liter, price_per_liter, amount, context=None):

        if amount > 0 and liter > 0:
            return {'value' : {'price_per_liter' : float(amount) / float(liter),}}
        elif amount > 0 and price_per_liter > 0:
            return {'value' : {'liter' : float(amount) / float(price_per_liter),}}
        elif liter > 0 and price_per_liter > 0:
            return {'value' : {'amount' : float(liter) * float(price_per_liter),}}
        else :
            return {}
        

    _name = 'fleet.vehicle.log.fuel'

    _columns = {
        'name' : fields.char('Name',size=64),

        'liter' : fields.float('Liter'),
        'price_per_liter' : fields.float('Price per liter'),
        'amount': fields.float('Total price'),
        'purchaser_id' : fields.many2one('res.partner', 'Purchaser'),
        'inv_ref' : fields.char('Invoice Reference', size=64),
        'vendor_id' : fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]"),
    }
    _defaults = {
        'purchaser_id': lambda self, cr, uid, ctx: uid,
    }

class fleet_vehicle_log_services(osv.Model):

    _inherits = {'fleet.vehicle.odometer': 'odometer_id'}    

    _name = 'fleet.vehicle.log.services'
    _columns = {

        'name' : fields.char('Name',size=64),
        
        'amount' :fields.float('Cost', help="Total cost of the service"),
        'service_ids' :fields.many2many('fleet.service.type','vehicle_service_type_rel','vehicle_service_type_id','service_id','Services completed'),
        'purchaser_id' : fields.many2one('res.partner', 'Purchaser'),
        'inv_ref' : fields.char('Invoice Reference', size=64),
        'vendor_id' :fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]"),
    }
    _defaults = {
        'purchaser_id': lambda self, cr, uid, ctx: uid,
    }

class fleet_insurance_type(osv.Model):
    _name = 'fleet.insurance.type'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

class fleet_vehicle_log_insurance(osv.Model):
    _inherits = {'fleet.vehicle.odometer': 'odometer_id'}

    _name = 'fleet.vehicle.log.insurance'
    _columns = {

        'name' : fields.char('Name',size=64),

        'insurance_type' : fields.many2one('fleet.insurance.type', 'Type', required=False, help='Type of the insurance'),
        'start_date' : fields.date('Start date', required=False, help='Date when the coverage of the insurance begins'),
        'expiration_date' : fields.date('Expiration date', required=False, help='Date when the coverage of the insurance expirates'),
        'price' : fields.float('Price', help="Cost of the insurance for the specified period"),
        'insurer_id' :fields.many2one('res.partner', 'Insurer', domain="[('supplier','=',True)]"),
        'purchaser_id' : fields.many2one('res.partner', 'Purchaser'),
        'ins_ref' : fields.char('Insurance Reference', size=64),
    }
    _defaults = {
        'purchaser_id': lambda self, cr, uid, ctx: uid,
    }

class fleet_service_type(osv.Model):
    _name = 'fleet.service.type'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

#class hr_employee(osv.Model):
#    _inherit = 'hr.employee'

#    _columns = {
#        'vehicle_id' : fields.one2many('fleet.vehicle','driver', 'Vehicle',type="char"),
#        'log_ids' : fields.one2many('fleet.vehicle.log', 'employee_id', 'Logs'),
#    }

