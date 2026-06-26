from odoo import models, fields, api


class ProjectTaskDuplicateWizard(models.TransientModel):
    _name = 'project.task.duplicate.wizard'
    _description = 'Duplicate Task Detection Wizard'

    task_id = fields.Many2one('project.task', string='Source Task', required=True, readonly=True)
    top_k = fields.Integer(string='Maximum Results', default=5, required=True)
    threshold = fields.Float(string='Similarity Threshold', default=0.65, required=True)
    line_ids = fields.One2many(
        'project.task.duplicate.wizard.line',
        'wizard_id',
        string='Duplicate Candidates',
    )

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        for wizard in wizards:
            wizard._populate_duplicate_lines()
        return wizards

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ['task_id', 'top_k', 'threshold']):
            for wizard in self:
                wizard._populate_duplicate_lines()
        return res

    @api.onchange('top_k', 'threshold', 'task_id')
    def _onchange_parameters(self):
        if not self.task_id:
            self.line_ids = [(5, 0, 0)]
            return

        self.env.cr.execute(
            "SELECT embedding::text FROM project_task_embedding WHERE task_id = %s",
            (self.task_id.id,)
        )
        res = self.env.cr.fetchone()
        if not res or not res[0]:
            self.line_ids = [(5, 0, 0)]
            return

        query_embedding = res[0]

        self.env.cr.execute("""
            SELECT task_id, 1 - (embedding <=> %s::vector) AS similarity
            FROM project_task_embedding
            WHERE task_id != %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, self.task_id.id, query_embedding, self.top_k or 5))

        db_results = self.env.cr.fetchall()

        lines = [(5, 0, 0)]
        for task_id_val, similarity in db_results:
            if similarity >= (self.threshold or 0.0):
                lines.append((0, 0, {
                    'task_id': task_id_val,
                    'similarity': similarity,
                }))
        self.line_ids = lines

    def _populate_duplicate_lines(self):
        self.ensure_one()
        # Clear existing lines first
        self.line_ids.unlink()

        if not self.task_id:
            return

        # Fetch the current task's embedding vector as text
        self.env.cr.execute(
            "SELECT embedding::text FROM project_task_embedding WHERE task_id = %s",
            (self.task_id.id,)
        )
        res = self.env.cr.fetchone()
        if not res or not res[0]:
            return

        query_embedding = res[0]

        # Query using HNSW index and cosine similarity operator (<=>)
        self.env.cr.execute("""
            SELECT task_id, 1 - (embedding <=> %s::vector) AS similarity
            FROM project_task_embedding
            WHERE task_id != %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, self.task_id.id, query_embedding, self.top_k or 5))

        db_results = self.env.cr.fetchall()

        lines_to_create = []
        for task_id_val, similarity in db_results:
            if similarity >= (self.threshold or 0.0):
                lines_to_create.append({
                    'wizard_id': self.id,
                    'task_id': task_id_val,
                    'similarity': similarity,
                })

        if lines_to_create:
            self.env['project.task.duplicate.wizard.line'].create(lines_to_create)


class ProjectTaskDuplicateWizardLine(models.TransientModel):
    _name = 'project.task.duplicate.wizard.line'
    _description = 'Duplicate Task Candidate Line'
    _order = 'similarity desc'

    wizard_id = fields.Many2one('project.task.duplicate.wizard', string='Wizard', ondelete='cascade')
    task_id = fields.Many2one('project.task', string='Duplicate Task', required=True)
    similarity = fields.Float(string='Similarity Score', digits=(1, 4))

    # Related fields for better UI presentation
    project_id = fields.Many2one('project.project', related='task_id.project_id', string='Project', readonly=True)
    stage_id = fields.Many2one('project.task.type', related='task_id.stage_id', string='Stage', readonly=True)
    user_ids = fields.Many2many('res.users', related='task_id.user_ids', string='Assignees', readonly=True)

    def action_open_task(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.task',
            'res_id': self.task_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
