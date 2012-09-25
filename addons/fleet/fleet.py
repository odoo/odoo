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


    def action_showLog(self, cr, uid, ids, context=None):
        """ This opens log view to view and add new log for this vehicle
            @return: 
        """
        print 'HELLO YOU--------------------------------------------'
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid ,'fleet','fleet_vehicle_log_act', context)
        return res
        #res['context'] = {
        #    'default_partner_ids': applicant.partner_id and [applicant.partner_id.id] or False,
        #    'default_user_id': uid,
        #    'default_state': 'open',
        #    'default_name': applicant.name,
        #    'default_categ_ids': category and [category.id] or False,
        #}
        #return res

    _name = 'fleet.vehicle'
    _description = 'Fleet Vehicle'

    _columns = {
        'name' : fields.function(_vehicle_name_get_fnc, type="char", string='Name', store=True),
        'registration' : fields.char('Registration', size=32, required=True, help='Registration number of the vehicle (ie: plate number for a car)'),
        'vin_sn' : fields.char('Chassis Number', size=32, required=False, help='Unique number written on the vehicle motor (VIN/SN number)'),
        'driver' : fields.many2one('hr.employee', 'Driver',required=False, help='Driver of the vehicle'),
        'model_id' : fields.many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle'),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'vehicle_id', 'Other Logs'),
        'log_fuel' : fields.one2many('fleet.vehicle.log.fuel','vehicle_id', 'Fuel Logs'),
        'log_services' : fields.one2many('fleet.vehicle.log.services','vehicle_id', 'Services Logs'),
        'log_insurances' : fields.one2many('fleet.vehicle.log.insurance','vehicle_id', 'Insurances'),
        'log_odometer' : fields.one2many('fleet.vehicle.log.odometer','vehicle_id', 'Odometer'),
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
    def create(self, cr, uid, data, context=None):
        vehicle_id = super(fleet_vehicle, self).create(cr, uid, data, context=context)
        try:
            vehicle = self.browse(cr, uid, vehicle_id, context=context)
            self.message_post(cr, uid, [vehicle_id], body='Vehicle %s has been added to the fleet!' % (vehicle.name), context=context)
        except:
            pass # group deleted: do not push a message
        return vehicle_id

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
            print 'Debug :' + str(liter) + ' | ' + str(price_per_liter) + ' | ' + str(amount)
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
        'liter' : fields.float('Liter'),
        'price_per_liter' : fields.float('Price per liter'),
        'amount': fields.float('Total price'),
        'inv_ref' : fields.char('Invoice Ref.', size=32),
        'vendor_id' :fields.many2one('res.partner', 'Vendor', domain="[('supplier','=',True)]"),
        'log_odometer_id' :fields.many2one('fleet.vehicle.log.odometer', 'Odometer Log'),
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

class fleet_service_type(osv.Model):
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

class fleet_vehicle_log_odometer(osv.Model):
    _inherit = ['fleet.vehicle.log']

    _name = 'fleet.vehicle.log.odometer'
    _columns = {
        'value' : fields.float('Value', required=True, help="Meter reading at service, fuel up and others"),
    }
    _defaults = {
        'name': 'Odometer Log',
        'type': 'Odometer'}

class hr_employee(osv.Model):
    _inherit = 'hr.employee'

    _columns = {
        'vehicle_id' : fields.one2many('fleet.vehicle','driver', 'Vehicle',type="char"),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'employee_id', 'Logs'),
    }

