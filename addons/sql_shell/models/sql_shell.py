from psycopg2 import Error as Psycopg2Error
import json

from odoo import models, fields, api

class SQLShell(models.Model):
    _name = 'sql.shell'
    _description = 'SQL Shell'
    _auto = False
    _table_query = "1"

    query = fields.Text(store=False)
    run = fields.Boolean(default=True, store=False)  # Act as a button
    result = fields.Json(store=False)
    max_rows = fields.Integer(default=1000, store=False, help="Protection to avoid fetching too many lines.")

    def _get_cr(self):
        # Allow setting custom cursors based on access rights and/or config parameters.
        # For instance, one can add `self.env.cr.execute("SET TRANSACTION READ ONLY")` in an
        # extension of this method, depending on access rights and/or server configuration for
        # instance to restrict usage and abuse.
        return self.env.cr

    @api.onchange('run')
    def _onchange_query(self):
        self.run = True
        if self.query:
            cr = self._get_cr()
            try:
                with cr.savepoint():
                    cr.execute(self.query)   # pylint: disable=sql-injection
                    if cr.rowcount > self.max_rows:
                        self.result = {'header': ['Message'], 'rows': [[
                            "The maximum number of lines has been exceeded (%s > %s)" % (cr.rowcount, self.max_rows)
                        ]]}
                    elif cr.description:
                        self.result = {
                            'header': [d.name for d in cr.description],
                            'rows': json.loads(json.dumps(cr.fetchall(), default=str)),  # TODO hack to serialize datetime objects, maybe monkeypatch cr.cast instead?
                        }
                    else:
                        # Manage queries that don't return anything (i.e. UPDATE)
                        self.result = {'header': ['Status'], 'rows': [[cr.statusmessage]]}
            except Psycopg2Error as e:
                self.result = {'header': ['Error'], 'rows': [[str(e)]]}

    def onchange(self, values, field_name, field_onchange):
        result = super().onchange(values, field_name, field_onchange)
        result['value'].pop('query', None)  # never change the user input
        return result
