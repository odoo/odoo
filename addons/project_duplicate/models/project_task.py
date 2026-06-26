import logging
import math
import zlib
from odoo import models, fields, api
from odoo.tools import config
from odoo.addons.project_duplicate.services.embedding_service import EmbeddingService
try:
    from odoo.tools.mail import html_to_inner_content
except ImportError:
    from odoo.tools import html_to_inner_content

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            if task.name or task.description:
                task._schedule_embedding_job()
        return tasks

    def write(self, vals):
        check_embedding = 'name' in vals or 'description' in vals
        res = super().write(vals)
        if check_embedding and res:
            for task in self:
                task._schedule_embedding_job()
        return res

    def _schedule_embedding_job(self):
        self.ensure_one()
        if config['test_enable'] and not self.env.context.get('test_project_duplicate'):
            return
        cron_code = f"model._generate_embedding({self.id})"

        # Avoid duplicating pending jobs
        existing_cron = self.env['ir.cron'].sudo().search([
            ('model_id.model', '=', 'project.task'),
            ('code', '=', cron_code),
            ('active', '=', True)
        ], limit=1)

        if not existing_cron:
            model = self.env['ir.model'].sudo().search([('model', '=', 'project.task')], limit=1)
            model_id = model.id if model else False

            self.env['ir.cron'].sudo().create({
                'name': f"Generate Embedding for Task {self.id}",
                'model_id': model_id,
                'state': 'code',
                'code': cron_code,
                'user_id': self.env.ref('base.user_root').id,
                'interval_number': 1,
                'interval_type': 'days',
                'nextcall': fields.Datetime.now(),
                'active': True,
            })

    @api.model
    def _generate_embedding(self, task_id):
        task = self.sudo().browse(task_id)
        if not task.exists():
            return

        name = task.name or ""
        description_html = task.description or ""
        description_text = html_to_inner_content(description_html) if description_html else ""

        content = f"{name} {description_text}".strip()
        if not content:
            return

        content_hash = str(zlib.crc32(content.encode('utf-8')))

        # Check existing embedding and hash
        self.env.cr.execute(
            "SELECT content_hash FROM project_task_embedding WHERE task_id = %s",
            (task_id,)
        )
        db_res = self.env.cr.fetchone()
        if db_res and db_res[0] == content_hash:
            return  # Skip, unchanged

        # Generate embedding vector
        service = EmbeddingService()
        vector = service.encode(content)
        if not vector or all(math.isclose(v, 0.0, abs_tol=1e-9) for v in vector):
            _logger.warning("Could not generate valid embedding for task ID %s", task_id)
            return

        vector_str = f"[{','.join(map(str, vector))}]"

        # Raw SQL write bypassing Odoo ORM to support pgvector custom type
        self.env.cr.execute("""
            INSERT INTO project_task_embedding (task_id, embedding, content_hash, embedding_dim, last_indexed)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (task_id) DO UPDATE
            SET embedding = EXCLUDED.embedding,
                content_hash = EXCLUDED.content_hash,
                last_indexed = EXCLUDED.last_indexed
        """, (task_id, vector_str, content_hash, 384, fields.Datetime.now()))

        # Deactivate the current cron since it is a single-run async task
        cron_id = self.env.context.get('cron_id')
        if cron_id:
            cron = self.env['ir.cron'].sudo().browse(cron_id)
            if cron.exists() and 'Generate Embedding for Task' in cron.name:
                cron.write({'active': False})

    @api.model
    def _cron_generate_missing_embeddings(self):
        """
        Delegates the bulk embedding generation to the EmbeddingService.
        """
        EmbeddingService().cron_generate_missing_embeddings(self.env)

    def action_detect_duplicates(self):
        self.ensure_one()
        # Synchronously update embedding for current task before searching
        self._generate_embedding(self.id)

        wizard = self.env['project.task.duplicate.wizard'].create({
            'task_id': self.id,
            'top_k': 5,
        })
        return {
            'name': 'Detect Duplicate Tasks',
            'type': 'ir.actions.act_window',
            'res_model': 'project.task.duplicate.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }
