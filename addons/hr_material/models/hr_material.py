
from lxml import etree

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import html2plaintext

class maintenance_request_stage(osv.Model):
    """Stages for Kanban view of Maintenance Request"""

    _name = 'maintenance.request.stage'
    _description = 'Maintenance Request Stage'
    _order = 'sequence asc'

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'sequence': fields.integer('Sequence'),
        'fold': fields.boolean('Folded in Kanban View'),
    }
    _defaults = {
        'sequence': 1,
    }
    _sql_constraints = [
        ('positive_sequence', 'CHECK(sequence >= 0)', 'Sequence number MUST be a natural')
    ]


class hr_material_category(osv.Model):
    _name = 'hr.material.category'
    _inherits = {"mail.alias": "alias_id"}
    _inherit = ['mail.thread']
    _description = 'Material Category'

    def _material_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for material in self.browse(cr, uid, ids, context):
            res[material.id] = len(material.material_ids)
        return res

    def _maintenance_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for maintenance in self.browse(cr, uid, ids, context):
            res[maintenance.id] = len(maintenance.maintenance_ids)
        return res

    _columns = {
        'name': fields.char('Category Name', required=True, size=64, translate=True),
        'user_id': fields.many2one('res.users', 'Responsible', track_visibility='onchange'),
        'color': fields.integer('Color Index'),
        'note': fields.text('Comments', translate=True),
        'material_ids': fields.one2many('hr.material', 'category_id', 'Materials'),
        'material_count': fields.function(_material_count, type='integer', string="Material"),
        'maintenance_ids': fields.one2many('hr.material.maintenance_request', 'category_id', domain=[('stage_id.fold', '=', False)]),
        'maintenance_count': fields.function(_maintenance_count, type='integer', string="Maintenance"),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
            help="Email alias for this material category. New emails will automatically "
                 "create new maintenance request for this material category."),
    }

    _defaults = {
        'user_id': lambda obj, cr, uid, ctx=None: uid,
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        alias_context = dict(context, alias_model_name='hr.material.maintenance_request', alias_parent_model_name=self._name)
        category_id = super(hr_material_category, self).create(cr, uid, vals, context=alias_context)
        category_rec = self.browse(cr, uid, category_id, context=context)
        self.pool.get('mail.alias').write(cr, uid, [category_rec.alias_id.id], {'alias_parent_thread_id': category_id, 'alias_defaults': {'category_id': category_id}}, context)
        return category_id

    def unlink(self, cr, uid, ids, context=None):
        alias_ids = []
        mail_alias = self.pool.get('mail.alias')
        for category in self.browse(cr, uid, ids, context=context):
            if category.material_ids or category.maintenance_ids:
                raise osv.except_osv(_('Invalid Action!'),
                                     _('You cannot delete a Material Category containing Material/Maintenance Request. You can either delete all the material/maintenance which belongs to in this category and then delete the material category.'))
            elif category.alias_id:
                alias_ids.append(category.alias_id.id)
        res = super(hr_material_category, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'material_ids': [], 'maintenance_ids': []})
        return super(hr_material_category, self).copy_data(cr, uid, id, default, context=context)

class hr_material(osv.Model):
    _name = 'hr.material'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Material'
    _track = {
        'employee_id': {
            'hr_material.mt_mat_assign': lambda self, cr, uid, obj, ctx = None: obj.employee_id,
        },
        'department_id': {
            'hr_material.mt_mat_assign': lambda self, cr, uid, obj, ctx = None: obj.department_id,
        },
    }

    def _maintenance_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x, 0), ids))
        for material in self.browse(cr, uid, ids, context):
            res[material.id] = len(material.maintenance_ids)
        return res

    _columns = {
        'name': fields.char('Name', required=True, size=64, translate=True),
        'user_id': fields.many2one('res.users', 'Technician', track_visibility='onchange'),
        'employee_id': fields.many2one('hr.employee', 'Assigned to Employee', track_visibility='onchange'),
        'department_id': fields.many2one('hr.department', 'Assigned to Department', track_visibility='onchange'),
        'category_id': fields.many2one('hr.material.category', 'Category', track_visibility='onchange'),
        'partner_id': fields.many2one('res.partner', 'Supplier', domain="[('supplier', '=', 1)]"),
        'model': fields.char('Model'),
        'serial_no': fields.char('Serial Number'),
        'assign_date': fields.date('Assigned Date', track_visibility='onchange'),
        'cost': fields.float('Cost'),
        'note': fields.text('Note', translate=True),
        'color': fields.integer('Color Index'),
        'scrap_date': fields.date('Scrap Date'),
        'material_assign_to': fields.selection([('employee','By Employee'),('department','By Department')], 'Assigned to', help='By Employee: Material assigned to individual Employee, By Department: Material assigned to group of employees in department', required=True),
        'maintenance_ids': fields.one2many('hr.material.maintenance_request', 'material_id', domain=[('stage_id.fold', '=', False)]),
        'maintenance_count': fields.function(_maintenance_count, type='integer', string="Maintenance"),
    }

    _defaults = {
        'material_assign_to': 'employee'
    }

    _sql_constraints = [
        ('serial_no', 'unique(serial_no)', "The serial number of this material must be unique !"),
    ]

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        if 'employee_id' in vals or 'department_id' in vals: 
            if vals.get('employee_id', False) or vals.get('department_id', False):
                vals['assign_date'] = fields.date.context_today(self, cr, uid, context=context)
        new_id = super(hr_material, self).create(cr, uid, vals, context=create_context)
        # subscribe employee or department manager when material assign to him.
        material = self.browse(cr, uid, new_id, context=context)
        if material.employee_id and material.employee_id.user_id:
            self.message_subscribe_users(cr, uid, [new_id], user_ids=[material.employee_id.user_id.id])
        if material.department_id and material.department_id.manager_id and material.department_id.manager_id.user_id:
            self.message_subscribe_users(cr, uid, [new_id], user_ids=[material.department_id.manager_id.user_id.id])
        return new_id

    def write(self, cr, uid, ids, vals, context=None):
        # subscribe employee or department manager when material assign to him.
        if 'employee_id' in vals and vals.get('employee_id', False):
            user_id = self.pool.get('hr.employee').browse(cr, uid, vals['employee_id'], context=context)['user_id']
            if user_id:
                self.message_subscribe_users(cr, uid, ids, user_ids=[user_id.id])
        if 'department_id' in vals and vals.get('department_id', False):
            department = self.pool.get('hr.department').browse(cr, uid, vals['department_id'], context=context)
            if department and department.manager_id and department.manager_id.user_id:
                self.message_subscribe_users(cr, uid, ids, user_ids=[department.manager_id.user_id.id])

        return super(hr_material, self).write(cr, uid, ids, vals, context=context)

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'serial_no': False})
        return super(hr_material, self).copy_data(cr, uid, id, default, context=context)

    def onchange_material_assign_to(self, cr, uid, ids, material_assign_to, context=None):
        if not material_assign_to:
            return {'value': {}}
        if material_assign_to == 'employee':
            return {'value': {'department_id': False}}
        else:
            return {'value': {'employee_id': False}}

    def onchange_category_id(self, cr, uid, ids, category_id, context=None):
        if not category_id:
            return {'value': {}}
        category = self.pool.get('hr.material.category').browse(cr, uid, category_id, context=context)
        return {'value': {'user_id': category.user_id.id}}

class hr_material_maintenance_request(osv.Model):
    _name = 'hr.material.maintenance_request'
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = 'Maintenance Request'
    _track = {
        'stage_id': {
            'hr_material.mt_req_created': lambda self, cr, uid, obj, ctx = None: obj.stage_id and obj.stage_id.sequence <= 1,
            'hr_material.mt_req_status': lambda self, cr, uid, obj, ctx = None: obj.stage_id and obj.stage_id.sequence > 1,
        } }

    def _employee_get(self, cr, uid, context=None):
        ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
        if ids:
            return ids[0]
        return False

    _columns = {
        'name':fields.char('Subjects', required=True, size=64, translate=True),
        'description': fields.text('Description'),
        'request_date': fields.date('Request Date', track_visibility='onchange'),
        'employee_id': fields.many2one('hr.employee', "Employee"),
        'department_id': fields.many2one('hr.department', 'Department'),
        'category_id': fields.many2one('hr.material.category', 'Category'),
        'material_id': fields.many2one('hr.material', 'Material'),
        'user_id': fields.many2one('res.users', 'Assigned to', track_visibility='onchange'),
        'stage_id': fields.many2one('maintenance.request.stage', string="Stage", ondelete="set null", track_visibility='onchange'),
        'priority': fields.selection([('4', 'Very Low'), ('3', 'Low'), ('2', 'Medium'), ('1', 'Urgent')], string='Priority', select=True),
        'color': fields.integer('Color Index'),
        'close_date': fields.date('Close Date'),
    }

    def _default_stage(self, cr, uid, context=None):
        ids = self.pool['maintenance.request.stage'].search(cr, uid, [], limit=1, context=context)
        if ids:
            return ids[0]
        return False

    _defaults = {
        'stage_id': lambda self, *a, **kw: self._default_stage(*a, **kw),
        'employee_id': _employee_get,
        'request_date': fields.date.context_today
    }

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        """ Read group customization in order to display all the stages in the
        kanban view, even if they are empty """
        stage_obj = self.pool.get('maintenance.request.stage')
        order = stage_obj._order
        access_rights_uid = access_rights_uid or uid

        if read_group_order == 'stage_id desc':
            order = '%s desc' % order

        stage_ids = stage_obj._search(cr, uid, [], order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)

        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        # override of fields_view_get in order to remove the clickable attribute from stage when user is not HRmanager
        if context is None:
            context = {}
        res = super(hr_material_maintenance_request, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if not self.pool.get('res.users').has_group(cr, uid, 'base.group_hr_manager'):
            if view_type == 'form':
                doc = etree.XML(res['arch'])
                for node in doc.xpath("//field[@name='stage_id']"):
                    if node.attrib['clickable']: del node.attrib['clickable']
                res['arch'] = etree.tostring(doc)
        return res

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        if 'category_id' in custom_values:
            category_id = custom_values['category_id']
            user_id = self.pool.get('hr.material.category').browse(cr, uid, category_id, context=context)['user_id']
            if user_id:
                custom_values['user_id'] = user_id.id
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''

        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'description': desc,
            'employee_id': False,
        }
        defaults.update(custom_values)
        return super(hr_material_maintenance_request, self).message_new(cr, uid, msg, custom_values=defaults, context=context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        return super(hr_material_maintenance_request, self).create(cr, uid, vals, context=create_context)


    def set_priority(self, cr, uid, ids, priority, *args):
        """Set priority
        """
        return self.write(cr, uid, ids, {'priority' : priority})

    def onchange_dept_emp_id(self, cr, uid, ids, employee_id, department_id, context=None):
        domain = []
        if department_id:
            domain = [('department_id', '=', department_id)]
        if employee_id and department_id:
            domain = ['|'] + domain
        if employee_id:
            domain = domain + [('employee_id', '=', employee_id)]
        return {'domain': {'material_id': domain}}

    def onchange_material_id(self, cr, uid, ids, material_id, context=None):
        if not material_id:
            return {'value': {}}
        material = self.pool.get('hr.material').browse(cr, uid, material_id, context=context)
        return {'value': {'user_id': material.user_id.id, 'category_id': material.category_id.id}}

    def onchange_category_id(self, cr, uid, ids, category_id, context=None):
        if not category_id:
            return {'value': {}}
        category = self.pool.get('hr.material.category').browse(cr, uid, category_id, context=context)
        return {'value': {'user_id': category.user_id.id}}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
