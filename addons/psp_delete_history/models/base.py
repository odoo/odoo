# models/base_model_inherit.py
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class BaseModelInherit(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def unlink(self):
        # Custom logic before the delete operation
        cr = self._cr
        for record in self:
            cr.execute("select * from %s where id=%d"%(record._name.replace(".", "_"), record.id))
            note = cr.dictfetchone()
            name = record._name + "," + str(record.id)
            self.env['res.delete.history'].create({
                'name': name,
                'model': record._name,
                'note': note,
                'date': fields.Datetime.now(),
                'res_id': record.id,
                'user_id': record.env.user.id,
            })
        _logger.info(f"Successfully recorded delete history.")

        # Call the original unlink method
        result = super(BaseModelInherit, self).unlink()

        return result
