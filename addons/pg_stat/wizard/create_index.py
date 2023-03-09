from ast import literal_eval

from odoo import models, fields, api


class CreateIndex(models.TransientModel):
    _name = 'pg.create.index'
    _description = "Create Postgresql indexes"

    unique = fields.Boolean()
    index_type = fields.Selection(
        selection=[
            ('btree', 'btree'),
            ('gin', 'gin'),
        ],
        default='btree',
        required=True,
    )
    model_id = fields.Many2one('ir.model', required=True)
    model_name = fields.Char(compute='_compute_model_name')
    field_ids = fields.Many2many(
        comodel_name='ir.model.fields',
        required=True,
        domain="[('model_id', '=', model_id), ('store', '=', True), ('ttype', 'not in', ('one2many', 'many2many'))]"
    )
    domain = fields.Char(default="[]")
    domain_is_valid = fields.Boolean(compute='_compute_where_clause')
    where_clause = fields.Char(compute='_compute_where_clause')
    where_params = fields.Binary(compute='_compute_where_clause')
    query = fields.Char(compute='_compute_query')

    @api.depends('model_id')
    def _compute_model_name(self):
        for record in self:
            record.model_name = record.model_id.model

    @api.depends('domain', 'model_name')
    def _compute_where_clause(self):
        self.where_clause = False
        self.where_params = False
        self.domain_is_valid = False
        for record in self.filtered('model_name'):
            query = self.env[record.model_name]._where_calc(literal_eval(record.domain))
            if len(query._tables) == 1:
                _select, where_clause, where_params = query.get_sql()
                if 'SELECT' not in where_clause:
                    record.domain_is_valid = True
                    record.where_clause = where_clause
                    record.where_params = where_params

    @api.depends('unique', 'index_type', 'model_name', 'field_ids', 'where_clause')
    def _compute_query(self):
        for record in self:
            table_name = self.env[record.model_name]._table if record.model_name else "???"
            index_name = f"custom_index_{record.id or '###'}"
            unique = "UNIQUE" if record.unique else ""
            columns = ', '.join(self.field_ids.mapped('name'))
            where = f"WHERE {record.where_clause}" if record.where_clause else ''
            record.query = self.env.cr.mogrify(
                f"""CREATE {unique} INDEX "{index_name}" ON "{table_name}" USING {record.index_type} ({columns}) {where}""",
                record.where_params
            )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            self.env.cr.execute(record.query)  # pylint: disable=sql-injection
        return records
