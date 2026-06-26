from odoo import models, fields


class ProjectTaskEmbedding(models.Model):
    _name = 'project.task.embedding'
    _description = 'Project Task Embedding'

    task_id = fields.Many2one('project.task', string='Task', ondelete='cascade', index=True, required=True)
    # Prefetch is False so Odoo doesn't load it during normal model reads
    embedding = fields.Binary(string='Embedding Vector', prefetch=False)
    content_hash = fields.Char(string='Content Hash', size=32, index=True)
    embedding_dim = fields.Integer(string='Embedding Dimension', default=384)
    last_indexed = fields.Datetime(string='Last Indexed')

    _task_uniq = models.Constraint('UNIQUE (task_id)', 'An embedding already exists for this task.')
