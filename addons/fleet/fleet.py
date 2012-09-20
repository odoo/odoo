from osv import osv, fields

class fleet_vehicle_model(osv.Model):
    _name = 'fleet.vehicle.type'
    _description = 'Type of the vehicle'
    _columns = {
        'name' : fields.char('Name', size=32, required=True),
    }

class fleet_vehicle_model(osv.Model):
    _name = 'fleet.vehicle.model'
    _description = ''

    _columns = {
        'brand' : fields.many2one('fleet.vehicle.model.brand', 'brand', required=True),
        'type' : fields.many2one('fleet.vehicle.type', 'Vehicle Type', required=True),
        'name' : fields.char('Name', size=32, required=True),
        'make' : fields.char('Make',size=32,required=True),
        'partner_id': fields.many2many('res.partner','fleet_vehicle_model_vendors','model_id', 'partner_id',string='Vendors',required=False),
    }

class fleet_vehicle_model_brand(osv.Model):
    _name = 'fleet.vehicle.model.brand'
    _description = 'Brand model of the vehicle'
    _columns = {
        'name' : fields.char('Brand Name',size=32, required=True),
    }

class fleet_vehicle(osv.Model):
    _name = 'fleet.vehicle'
    _description = 'Fleet Vehicle'

    _columns = {
        'registration' : fields.char('Registration', size=32, required=True),
        'driver' : fields.many2one('fleet.vehicle', 'employee_id', required=False),
        'model_id' : fields.many2one('fleet.vehicle.model', 'Model', required=True),
        'log_ids' : fields.one2many('fleet.vehicle.log', 'vehicle_id', 'Logs'),

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