import logging

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import fields
from openerp.osv.orm import Model

_logger = logging.getLogger(__name__)

class ir_model_constraint(Model):
    """
    This model tracks PostgreSQL foreign keys and constraints used by OpenERP
    models.
    """
    _name = 'ir.model.constraint'
    _columns = {
        'name': fields.char('Constraint', required=True, size=128, select=1,
            help="PostgreSQL constraint or foreign key name."),
        'model': fields.many2one('ir.model', string='Model',
            required=True, select=1),
        'module': fields.many2one('ir.module.module', string='Module',
            required=True, select=1),
        'type': fields.char('Constraint Type', required=True, size=1, select=1,
            help="Type of the constraint: `f` for a foreign key, "
                "`u` for other constraints."),
        'date_update': fields.datetime('Update Date'),
        'date_init': fields.datetime('Initialization Date')
    }

    _sql_constraints = [
        ('module_name_uniq', 'unique(name, module)',
            'Constraints with the same name are unique per module.'),
    ]

    def _module_data_uninstall(self, cr, uid, ids, context=None):
        """
        Delete PostgreSQL foreign keys and constraints tracked by this model.
        """ 

        if uid != SUPERUSER_ID and not self.pool.get('ir.model.access').check_groups(cr, uid, "base.group_system"):
            raise except_orm(_('Permission Denied'), (_('Administrator access is required to uninstall a module')))

        context = dict(context or {})

        ids_set = set(ids)
        ids.sort()
        ids.reverse()
        to_unlink = []
        for data in self.browse(cr, uid, ids, context):
            model = data.model.model
            model_obj = self.pool.get(model)
            name = openerp.tools.ustr(data.name)
            typ = data.type

            # double-check we are really going to delete all the owners of this schema element
            cr.execute("""SELECT id from ir_model_constraint where name=%s""", (data.name,))
            external_ids = [x[0] for x in cr.fetchall()]
            if (set(external_ids)-ids_set):
                # as installed modules have defined this element we must not delete it!
                continue

            if typ == 'f':
                # test if FK exists on this table (it could be on a related m2m table, in which case we ignore it)
                cr.execute("""SELECT 1 from pg_constraint cs JOIN pg_class cl ON (cs.conrelid = cl.oid)
                              WHERE cs.contype=%s and cs.conname=%s and cl.relname=%s""", ('f', name, model_obj._table))
                if cr.fetchone():
                    cr.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (model_obj._table, name),)
                    _logger.info('Dropped FK CONSTRAINT %s@%s', name, model)

            if typ == 'u':
                # test if constraint exists
                cr.execute("""SELECT 1 from pg_constraint cs JOIN pg_class cl ON (cs.conrelid = cl.oid)
                              WHERE cs.contype=%s and cs.conname=%s and cl.relname=%s""", ('u', name, model_obj._table))
                if cr.fetchone():
                    cr.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (model_obj._table, name),)
                    _logger.info('Dropped CONSTRAINT %s@%s', name, model)

            to_unlink.append(data.id)
        self.unlink(cr, uid, to_unlink, context)
