import datetime

from odoo import api, fields, models


class TestOrmAutovacuumed(models.Model):
    _name = 'test_orm.autovacuumed'
    _description = 'test_orm.autovacuumed'

    expire_at = fields.Datetime('Expires at')

    @api.autovacuum
    def _gc_simple(self):
        self.search([('expire_at', '<', datetime.datetime.now() - datetime.timedelta(days=1))]).unlink()

    @api.autovacuum
    def _gc_proper(self, limit=5):
        records = self.search([('expire_at', '<', datetime.datetime.now() - datetime.timedelta(days=1))], limit=limit)
        records.unlink()
        return len(records), len(records) == limit
