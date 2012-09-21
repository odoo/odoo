from osv import osv, fields

class fleet_vehicle_model_type(osv.Model):
    _name = 'fleet.vehicle.type'
    _description = 'Type of the vehicle'
    _columns = {
        'name' : fields.char('Name', size=32, required=True),
    }

class fleet_vehicle_model(osv.Model):
    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'

    _columns = {
        'name' : fields.char('Name',size=32, required=False),
        'brand' : fields.many2one('fleet.vehicle.model.brand', 'Model brand', required=False),
        'type' : fields.many2one('fleet.vehicle.type', 'Vehicle Type', required=False),
        'modelname' : fields.many2one('fleet.vehicle.model.name', 'Model name', required=False),
        'make' : fields.many2one('fleet.vehicle.model.make', 'Model make', required=False),
        'year' : fields.integer('Year', required=False),
        'partner_id': fields.many2many('res.partner','fleet_vehicle_model_vendors','model_id', 'partner_id',string='Vendors',required=False),
    
        'transmission' : fields.selection([('manual', 'Manual'),('automatic','Automatic')], 'Transmission', help='Transmission Used by the vehicle',required=False),
        'fuel_type' : fields.selection([('gasoline', 'Gasoline'),('diesel','Diesel'),('electric','Electric'),('hybrid','Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle',required=False),
        'horses' : fields.integer('Horses',required=False),
        'power' : fields.integer('Power (kW)',required=False,help='Power in kW of the vehicle'),
        'co2' : fields.float('CO2 Emissions',required=False,help='CO2 emissions of the vehicle'),
    }

class fleet_vehicle_model_brand(osv.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand model of the vehicle'
    _columns = {
        'name' : fields.char('Brand Name',size=32, required=True),
    }

class fleet_vehicle_model_name(osv.Model):
    _name = 'fleet.vehicle.model.name'
    _description = 'Name model of the vehicle'
    _columns = {
        'name' : fields.char('Name',size=32, required=True),
    }

class fleet_vehicle_model_make(osv.Model):
    _name = 'fleet.vehicle.model.make'
    _description = 'Make model of the vehicle'
    _columns = {
        'name' : fields.char('Make',size=32, required=True),
    }

class fleet_vehicle(osv.Model):
    _name = 'fleet.vehicle'
    _description = 'Fleet Vehicle'

    _columns = {
        'registration' : fields.char('Registration', size=32, required=False),
        'vin_sn' : fields.char('VIN SN', size=32, required=False),
        'driver' : fields.many2one('hr.employee', 'Driver',required=False),
        'model_id' : fields.many2one('fleet.vehicle.model', 'Model', required=True),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'vehicle_id', 'Logs'),
        'acquisition_date' : fields.date('Acquisition date', required=False),
        'acquisition_price' : fields.integer('Price'),
        'color' : fields.char('Color',size=32),
        'status' : fields.char('Status',size=32),
        'location' : fields.char('Location',size=32),

        'next_repair_km' : fields.integer('Next Repair Km'),
        'message' : fields.char('Message', size=128, readonly=True),
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

class fleet_vehicle_log_type(osv.Model):
    _name = 'fleet.vehicle.log.type'

    _columns = {
        'name' : fields.char('Name', size=32, required=True),
    }

class fleet_vehicle_log(osv.Model):
    _name = 'fleet.vehicle.log'

    _columns = {
        'employee_id' : fields.many2one('hr.employee', 'Employee', required=True),
        'vehicle_id' : fields.many2one('fleet.vehicle', 'Vehicle', required=True),

        'create_date' : fields.datetime('Creation Date', readonly=True),

        'description' : fields.text('Description'),
        'type' : fields.many2one('fleet.vehicle.log.type', 'Type', required=True),


    }

class hr_employee(osv.Model):
    _inherit = 'hr.employee'

    _columns = {
        'vehicle_id' : fields.many2one('fleet.vehicle', 'Vehicle', required=True),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'employee_id', 'Logs'),
    }