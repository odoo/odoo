from osv import osv, fields

class fleet_vehicle_model_type(osv.Model):
    _name = 'fleet.vehicle.type'
    _description = 'Type of the vehicle'
    _columns = {
        'name' : fields.char('Name', size=32, required=True),
    }
#comment to delete#comment to delete
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
        'brand' : fields.many2one('fleet.vehicle.model.brand', 'Model brand', required=False, help='Brand of the vehicle'),
        'vendors': fields.many2many('res.partner','fleet_vehicle_model_vendors','model_id', 'partner_id',string='Vendors',required=False),
    }

class fleet_vehicle_model_brand(osv.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand model of the vehicle'
    _columns = {
        'name' : fields.char('Brand Name',size=32, required=True),
    }

class fleet_vehicle(osv.Model):

    _inherit = 'mail.thread'

    def create_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            message = _("%s has been <b>created</b>.")% (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_post(cr, uid, [id], body=message, context=context)
        return True

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            if record.registration:
                name = record.registration
            if record.model_id.modelname:
                name = record.model_id.modelname + ' / ' + name
            if record.model_id.brand.name:
                name = record.model_id.brand.name+' / '+ name
            res.append((record.id, name))
        return res

    def _vehicle_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _name = 'fleet.vehicle'
    _description = 'Fleet Vehicle'

    _columns = {
        'name' : fields.function(_vehicle_name_get_fnc, type="char", string='Name', store=True),
        'registration' : fields.char('Registration', size=32, required=False, help='Registration number of the vehicle (ie: plate number for a car)'),
        'vin_sn' : fields.char('Chassis Number', size=32, required=False, help='Unique number written on the vehicle motor (VIN/SN number)'),
        'driver' : fields.many2one('hr.employee', 'Driver',required=False, help='Driver of the vehicle'),
        'model_id' : fields.many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle'),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'vehicle_id', 'Other Logs'),
        'log_fuel' : fields.one2many('fleet.vehicle.log.fuel','vehicle_id', 'Fuel Logs'),
        'log_services' : fields.one2many('fleet.vehicle.log.services','vehicle_id', 'Services Logs'),
        'log_insurances' : fields.one2many('fleet.vehicle.log.insurance','vehicle_id', 'Insurances'),
        'acquisition_date' : fields.date('Acquisition date', required=False, help='Date when the vehicle has been bought'),
        'acquisition_price' : fields.integer('Price', help='Price of the bought vehicle'),
        'color' : fields.char('Color',size=32, help='Color of the vehicle'),
        'status' : fields.char('Status',size=32, help='Status of the vehicle (in repair, active, ...)'),
        'location' : fields.char('Location',size=32, help='Location of the vehicle (garage, ...)'),
        'doors' : fields.integer('Number of doors', help='Number of doors of the vehicle'),

        'transmission' : fields.selection([('manual', 'Manual'),('automatic','Automatic')], 'Transmission', help='Transmission Used by the vehicle',required=False),
        'fuel_type' : fields.selection([('gasoline', 'Gasoline'),('diesel','Diesel'),('electric','Electric'),('hybrid','Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle',required=False),
        'horsepower' : fields.integer('Horsepower',required=False),
        'horsepower_tax': fields.float('Horsepower Taxation'),
        'power' : fields.integer('Power (kW)',required=False,help='Power in kW of the vehicle'),
        'co2' : fields.float('CO2 Emissions',required=False,help='CO2 emissions of the vehicle'),
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

class fleet_vehicle_log(osv.Model):
    _name = 'fleet.vehicle.log'

    _columns = {
        'name' : fields.char('Log',size=32),
        'employee_id' : fields.many2one('hr.employee', 'Employee', required=True),
        'vehicle_id' : fields.many2one('fleet.vehicle', 'Vehicle', required=True),

        'date_creation' : fields.date('Creation Date'),

        'description' : fields.text('Description'),
        'type' : fields.char('Type',size=32),
        }
        
    _defaults = {
            'name' : 'Log',
            'type' : 'Log',
    }

class fleet_vehicle_log_fuel(osv.Model):

    
    _inherit = ['fleet.vehicle.log','mail.thread']


    def _get_price(self, cr, uid, ids, fields, args, context=None):
        result = {}
        for record in self.browse(cr, uid, ids, context=None):
            res = record.liter * record.price_per_liter
            result[record.id] = {
                'amount' : res,
            }
        return result

    def on_change_fuel(self, cr, uid, ids, liter, price_per_liter, context=None):

        print 'Amount : ' + str(liter * price_per_liter)

        return {
            'value' : {
                'amount' : liter * price_per_liter,
            }
        }

        

    _name = 'fleet.vehicle.log.fuel'
    _columns = {
        'liter' : fields.float('Liter'),
        'price_per_liter' : fields.float('Price per liter'),
        'amount': fields.function(_get_price, type='float', multi='fuel', string='Total Price'),
        'inv_ref' : fields.char('Invoice Ref.', size=32),
    }
    _defaults = {
        'name': 'Fuel log',
        'type': 'Refueling',
        }

class fleet_insurance_type(osv.Model):
    _name = 'fleet.insurance.type'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

class fleet_vehicle_log_insurance(osv.Model):
    _inherit = 'fleet.vehicle.log'
    _name = 'fleet.vehicle.log.insurance'
    _columns = {
        'insurance_type' : fields.many2one('fleet.insurance.type', 'Type', required=False, help='Type of the insurance'),
        'start_date' : fields.date('Start date', required=False, help='Date when the coverage of the insurance begins'),
        'expiration_date' : fields.date('Expiration date', required=False, help='Date when the coverage of the insurance expirates'),
        'price' : fields.float('Price', help="Cost of the insurance for the specified period"),
        'insurer_id' :fields.many2one('res.partner', 'Insurer', domain="[('supplier','=',True)]"),
        'description' : fields.text('Description'),
    }
    _defaults = {
        'name': 'Insurance log',
        'type': 'Insurance',}

class service_type(osv.Model):
    _name = 'fleet.service.type'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

class fleet_vehicle_log_services(osv.Model):
    _inherit = ['fleet.vehicle.log']

    _name = 'fleet.vehicle.log.services'
    _columns = {
        'vendor_id' :fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]"),
        'amount' :fields.float('Cost', help="Total cost of the service"),
        'reference' :fields.char('Reference',size=128),
        'service_ids' :fields.many2many('fleet.service.type','vehicle_service_type_rel','vehicle_service_type_id','service_id','Services completed'),
    }
    _defaults = {
        'name': 'Service log',
        'type': 'Services'}

class hr_employee(osv.Model):
    _inherit = 'hr.employee'

    _columns = {
        'vehicle_id' : fields.one2many('fleet.vehicle','driver', 'Vehicle',type="char"),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'employee_id', 'Logs'),
    }

