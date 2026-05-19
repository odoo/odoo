from odoo import fields, models
from odoo.modules import module


class ModelData(models.Model):
    """
    External reference to records created via the populate.
    This allows referencing those records, either for modification during the populate process,
    or to remove them all at after testing.
    """
    _name = 'populate.model.data'
    _description = 'Reference to Populated Records.'
    _log_access = False

    res_model = fields.Char('Model', related='job_id.model_name')
    res_id = fields.Many2oneReference('Record', model_field='res_model', required=True,
        # skip deletion during testing to avoid changing too much query counts
        # this module is usually not installed in production
        ondelete=lambda self, ref: 'ignore' if module.current_test and 'populate' not in module.current_test.test_module else 'cascade',
    )

    job_id = fields.Many2one('populate.job', required=True, ondelete='cascade')
    ref = fields.Char(related='job_id.ref')
    session_id = fields.Many2one(related='job_id.session_id')
    blueprint_id = fields.Many2one(related='job_id.blueprint_id')

    _job_records_idx = models.UniqueIndex('(job_id, res_id)')
