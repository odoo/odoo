from osv import osv, fields

class fleet_vehicle_model_type(osv.Model):
    _name = 'fleet.vehicle.type'
    _description = 'Type of the vehicle'
    _columns = {
        'name' : fields.char('Name', size=32, required=True),
    }
#comment to delete
class fleet_vehicle_model(osv.Model):

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        reads = self.read(cr, uid, ids, ['type','brand','modelname','version','year'], context=context)
        res = []
        for record in reads:
            name = ''
            if record['type']:
                name = record['type'][1] + " - "
            if record['brand']:
                name = name + record['brand'][1]
            if record['modelname']:
                name = name+ ' / ' +record['modelname'][1]
            if record['version']:
                name = name+ ' / ' +record['version'][1]
            if record['year']:
                name = name+ ' / ' +str(record['year'])
            res.append((record['id'], name))
        return res

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'

    _columns = {
        'name' : fields.function(_name_get_fnc, type="char", string='Name'),
        'brand' : fields.many2one('fleet.vehicle.model.brand', 'Model brand', required=True, help='Brand of the vehicle'),
        'type' : fields.many2one('fleet.vehicle.type', 'Vehicle Type', required=True, help='Type of vehicle (car, bike, ...)'),
        'modelname' : fields.many2one('fleet.vehicle.model.name', 'Model name', required=False, help='Model name of the vehicle'),
        'version' : fields.one2many('fleet.vehicle.model.version', 'model_version_id', 'Versions'),
        'year' : fields.integer('Year', required=False, help='Year of fabrication of the vehicle'),
        'partner_id': fields.many2many('res.partner','fleet_vehicle_model_vendors','model_id', 'partner_id',string='Vendors',required=False),
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

class fleet_vehicle_model_version(osv.Model):
    _name = 'fleet.vehicle.model.version'
    _description = 'version model of the vehicle'
    _columns = {
        'name' : fields.char('name',size=32, required=True),
        'model_version_id' : fields.many2one('fleet.vehicle.model', 'Associated model', required=True, help='Model name of the vehicle associated to this version'),
    
        'transmission' : fields.selection([('manual', 'Manual'),('automatic','Automatic')], 'Transmission', help='Transmission Used by the vehicle',required=False),
        'fuel_type' : fields.selection([('gasoline', 'Gasoline'),('diesel','Diesel'),('electric','Electric'),('hybrid','Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle',required=False),
        'horsepower' : fields.integer('Horsepower',required=False),
        'horsepower_tax': fields.float('Horsepower Taxation'),
        'power' : fields.integer('Power (kW)',required=False,help='Power in kW of the vehicle'),
        'co2' : fields.float('CO2 Emissions',required=False,help='CO2 emissions of the vehicle'),
    }

class fleet_vehicle(osv.Model):
    _name = 'fleet.vehicle'
    _description = 'Fleet Vehicle'

    _columns = {
        'registration' : fields.char('Registration', size=32, required=False, help='Registration number of the vehicle (ie: plate number for a car)'),
        'vin_sn' : fields.char('Chassis Number', size=32, required=False, help='Unique number written on the vehicle motor (VIN/SN number)'),
        'driver' : fields.many2one('hr.employee', 'Driver',required=False, help='Driver of the vehicle'),
        'model_id' : fields.many2one('fleet.vehicle.model', 'Model', required=True, help='Model of the vehicle'),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'vehicle_id', 'Logs'),
        'acquisition_date' : fields.date('Acquisition date', required=False, help='Date when the vehicle has been bought'),
        'acquisition_price' : fields.integer('Price', help='Price of the bought vehicle'),
        'color' : fields.char('Color',size=32, help='Color of the vehicle'),
        'status' : fields.char('Status',size=32, help='Status of the vehicle (in repair, active, ...)'),
        'location' : fields.char('Location',size=32, help='Location of the vehicle (garage, ...)'),

        'next_repair_km' : fields.integer('Next Repair Km'),

        'transmission' : fields.selection([('manual', 'Manual'),('automatic','Automatic')], 'Transmission', help='Transmission Used by the vehicle',required=False),
        'fuel_type' : fields.selection([('gasoline', 'Gasoline'),('diesel','Diesel'),('electric','Electric'),('hybrid','Hybrid')], 'Fuel Type', help='Fuel Used by the vehicle',required=False),
        'horses' : fields.integer('Horses',required=False),
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