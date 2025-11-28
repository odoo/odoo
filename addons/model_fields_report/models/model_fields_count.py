from odoo import models, fields


class ModelFieldsCount(models.MaterializedModel):
    _name = 'model.fields.count'
    _description = 'Model Fields Count Report'
    _order = 'field_count desc, model'

    _default_refresh_mode = 'concurrently'
    _web_auto_refresh = True
    _stale_threshold = 5  # 5 seconds

    model = fields.Char(string='Model', readonly=True)
    field_count = fields.Integer(string='Field Count', readonly=True)

    def init(self):
        """
        Create the PostgreSQL materialized view.
        This method is called when the module is installed or upgraded.
        """
        self.env.cr.execute("SELECT 1 FROM pg_matviews WHERE matviewname = 'model_fields_count'")
        if self.env.cr.rowcount:
            return
        # TODO: support auto upgrade
        self.env.cr.execute("""
            CREATE MATERIALIZED VIEW model_fields_count AS (
                SELECT 
                    im.id as id,
                    im.model as model,
                    count(imf.id) as field_count
                FROM ir_model im
                JOIN ir_model_fields imf ON im.id = imf.model_id
                GROUP BY im.id, im.model
            );
            CREATE UNIQUE INDEX model_fields_count_id_idx ON model_fields_count (id);
        """)
