# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class IrLogging(models.Model):
    _name = 'ir.logging'
    _description = 'Logging'
    _order = 'id DESC'

    # The _log_access fields are defined manually for the following reasons:
    #
    # - The entries in ir_logging are filled in with sql queries bypassing the orm. As the --log-db
    #   cli option allows to insert ir_logging entries into a remote database, the one2many *_uid
    #   fields make no sense in the first place but we will keep it for backward compatibility.
    #
    # - Also, when an ir_logging entry is triggered by the orm (when using --log-db) at the moment
    #   it is making changes to the res.users model, the ALTER TABLE will aquire an exclusive lock
    #   on res_users, preventing the ir_logging INSERT to be processed, hence the ongoing module
    #   install/update will hang forever as the orm is blocked by the ir_logging query that will
    #   never occur.
    create_uid = fields.Integer(string='Created by', readonly=True)
    create_date = fields.Datetime(string='Created on', readonly=True)
    write_uid = fields.Integer(string='Last Updated by', readonly=True)
    write_date = fields.Datetime(string='Last Updated on', readonly=True)

    name = fields.Char(required=True)
    type = fields.Selection([('client', 'Client'), ('server', 'Server')], required=True, index=True)
    dbname = fields.Char(string='Database Name', index=True)
    level = fields.Char(index=True)
    message = fields.Text(required=True)
    path = fields.Char(required=True)
    func = fields.Char(string='Function', required=True)
    line = fields.Char(required=True)

    @api.model_cr
    def init(self):
        super(IrLogging, self).init()
        self._cr.execute("ALTER TABLE ir_logging DROP CONSTRAINT IF EXISTS ir_logging_write_uid_fkey")
