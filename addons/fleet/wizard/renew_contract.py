from osv import osv, fields
import datetime

class renew_contract(osv.TransientModel):
    _name = "fleet.vehicle.contract.renew"
    _description = "wizard to renew a contract"

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not ids:
            return []
        reads = self.browse(cr, uid, ids, context=context)
        res = []
        for record in reads:
            if record.vehicle_id.name:
                name = str(record.vehicle_id.name)
            if record.cost_type.name:
                name = name+ ' / '+ str(record.cost_type.name)
            if record.date:
                name = name+ ' / '+ record.date
            res.append((record.id, name))
        return res

    def _vehicle_contract_name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    def _get_odometer(self, cr, uid, ids, odometer_id, arg, context):
        res = dict.fromkeys(ids, False)
        for record in self.browse(cr,uid,ids,context=context):
            if record.odometer_id:
                res[record.id] = record.odometer_id.value
        return res

    def _set_odometer(self, cr, uid, id, name, value, args=None, context=None):
        if value:
            try:
                value = float(value)
            except ValueError:
                #_logger.exception(value+' is not a correct odometer value. Please, fill a float for this field')
                raise except_orm(_('Error!'), value+' is not a correct odometer value. Please, fill a float for this field')
               
            date = self.browse(cr, uid, id, context=context).date
            if not(date):
                date = time.strftime('%Y-%m-%d')
            vehicle_id = self.browse(cr, uid, id, context=context).vehicle_id
            data = {'value' : value,'date' : date,'vehicle_id' : vehicle_id.id}
            odometer_id = self.pool.get('fleet.vehicle.odometer').create(cr, uid, data, context=context)
            self.write(cr, uid, id, {'odometer_id': odometer_id})
            return value
        self.write(cr, uid, id, {'odometer_id': ''})
        return False

    def on_change_vehicle(self, cr, uid, ids, vehicle_id, context=None):

        if not vehicle_id:
            return {}

        odometer_unit = self.pool.get('fleet.vehicle').browse(cr, uid, vehicle_id, context=context).odometer_unit

        return {
            'value' : {
                'odometer_unit' : odometer_unit,
            }
        }

    def compute_next_year_date(self, strdate):
        oneyear=datetime.timedelta(days=365)
        curdate = self.str_to_date(strdate)
        nextyear=curdate+oneyear#int(strdate[:4])+1
        return str(nextyear)#+strdate[4:]

    #def on_change_start_date(self, cr, uid, ids, strdate, context=None):
    #    if (strdate):
           
    #        return {'value' : {'expiration_date' : self.compute_next_year_date(strdate),}}
    #    else:
    #        return {}

    def str_to_date(self,strdate):
        return datetime.datetime(int(strdate[:4]),int(strdate[5:7]),int(strdate[8:]))

    def get_warning_date(self,cr,uid,ids,prop,unknow_none,context=None):
        if context is None:
            context={}
        if not ids:
            return dict([])
        reads = self.browse(cr,uid,ids,context=context)
        res=[]
        for record in reads:
            #if (record.reminder==True):
            if (record.expiration_date and record.state=='open'):
                today=self.str_to_date(time.strftime('%Y-%m-%d'))
                renew_date = self.str_to_date(record.expiration_date)
                diff_time=int((renew_date-today).days)
                if (diff_time<=0):
                    res.append((record.id,0))
                else:
                    res.append((record.id,diff_time))
            else:
                res.append((record.id,-1))
            #else:
            #    res.append((record.id,-1))
        return dict(res)

    _columns = {
        'name' : fields.function(_vehicle_contract_name_get_fnc, type="text", string='Name', store=True),
        'vehicle_id': fields.many2one('fleet.vehicle', 'Vehicle', required=True, help='Vehicle concerned by this fuel log'),
        'cost_type': fields.many2one('fleet.service.type', 'Service type', required=False, help='Service type purchased with this cost'),
        'amount': fields.float('Total Price'),

        'parent_id': fields.many2one('fleet.vehicle.cost', 'Parent', required=False, help='Parent cost to this current cost'),
        'cost_ids' : fields.one2many('fleet.vehicle.cost', 'parent_id', 'Included Services'),

        'date' :fields.date('Date',help='Date when the cost has been executed'),

        'start_date' : fields.date('Contract Start Date', required=False, help='Date when the coverage of the contract begins'),
        'expiration_date' : fields.date('Contract Expiration Date', required=False, help='Date when the coverage of the contract expirates (by default, one year after begin date)'),
        'warning_date' : fields.function(get_warning_date,type='integer',string='Warning Date',store=False),

        'insurer_id' :fields.many2one('res.partner', 'Supplier', domain="[('supplier','=',True)]"),
        'purchaser_id' : fields.many2one('res.partner', 'Contractor',domain="['|',('customer','=',True),('employee','=',True)]",help='Person to which the contract is signed for'),
        'ins_ref' : fields.char('Contract Reference', size=64),
        'state' : fields.selection([('open', 'In Progress'), ('closed', 'Terminated')], 'Status', readonly=True, help='Choose wheter the contract is still valid or not'),
        #'reminder' : fields.boolean('Renewal Reminder', help="Warn the user a few days before the expiration date of this contract"),
        'notes' : fields.text('Terms and Conditions', help='Write here all supplementary informations relative to this contract'),
        'odometer_id' : fields.many2one('fleet.vehicle.odometer', 'Odometer', required=False, help='Odometer measure of the vehicle at the moment of this log'),
        'odometer' : fields.function(_get_odometer,fnct_inv=_set_odometer,type='char',string='Odometer Value',store=False,help='Odometer measure of the vehicle at the moment of this log'),
        'odometer_unit': fields.related('vehicle_id','odometer_unit',type="char",string="Unit",store=False, readonly=True),
        #'cost_amount': fields.related('cost_id','amount',type="float",string="Amount",store=True, readonly=True),
    }



    def renew(self, cr, uid, ids, context=None):
        print '-------------------------------'
        print 'renew contract'
        print '-------------------------------'
        return {}