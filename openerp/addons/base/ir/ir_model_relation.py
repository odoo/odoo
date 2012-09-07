import logging

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import fields
from openerp.osv.orm import Model

_logger = logging.getLogger(__name__)

class ir_model_relation(Model):
    """
    This model tracks PostgreSQL tables used to implement OpenERP many2many
    relations.
    """
    _name = 'ir.model.relation'
    _columns = {
        'name': fields.char('Relation Name', required=True, size=128, select=1,
            help="PostgreSQL table name implementing a many2many relation."),
        'model': fields.many2one('ir.model', string='Model',
            required=True, select=1),
        'module': fields.many2one('ir.module.module', string='Module',
            required=True, select=1),
        'date_update': fields.datetime('Update Date'),
        'date_init': fields.datetime('Initialization Date')
    }

    def _module_data_uninstall(self, cr, uid, ids, context=None):
        """
        Delete PostgreSQL many2many relations tracked by this model.
        """ 

        if uid != SUPERUSER_ID and not self.pool.get('ir.model.access').check_groups(cr, uid, "base.group_system"):
            raise except_orm(_('Permission Denied'), (_('Administrator access is required to uninstall a module')))

        ids_set = set(ids)
        to_drop_table = []
        ids.sort()
        ids.reverse()
        for data in self.browse(cr, uid, ids, context):
            model = data.model
            model_obj = self.pool.get(model)
            name = openerp.tools.ustr(data.name)

            # double-check we are really going to delete all the owners of this schema element
            cr.execute("""SELECT id from ir_model_relation where name = %s""", (data.name,))
            external_ids = [x[0] for x in cr.fetchall()]
            if (set(external_ids)-ids_set):
                # as installed modules have defined this element we must not delete it!
                continue

            cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name=%s", (name,))
            if cr.fetchone() and not name in to_drop_table:
                to_drop_table.append(name)

        self.unlink(cr, uid, ids, context)

        # drop m2m relation tables
        for table in to_drop_table:
            cr.execute('DROP TABLE %s CASCADE'% (table),)
            _logger.info('Dropped table %s', table)

        cr.commit()
