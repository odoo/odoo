import unittest
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.project_duplicate.services.embedding_service import FASTEMBED_AVAILABLE


@unittest.skipUnless(FASTEMBED_AVAILABLE, "fastembed library is required to run duplicate detector tests")
@tagged('post_install', '-at_install', 'project_duplicate')
class TestDuplicateDetector(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, test_project_duplicate=True))
        cls.project = cls.env['project.project'].create({
            'name': 'Test Project',
        })

    def test_01_embedding_generation_on_create_write(self):
        """Test that scheduling embedding job is triggered on create and write"""
        # Create a task
        task = self.env['project.task'].create({
            'name': 'Deploy new backend database',
            'description': '<p>Configure PostgreSQL database with pgvector extension</p>',
            'project_id': self.project.id,
        })

        # Check that a cron job was scheduled
        crons_after_create = self.env['ir.cron'].search([
            ('model_id.model', '=', 'project.task'),
            ('code', '=', f"model._generate_embedding({task.id})")
        ])
        self.assertTrue(crons_after_create, "A cron job should be scheduled after task creation")

        # Run the embedding generation synchronously for testing
        task._generate_embedding(task.id)

        # Verify embedding record is created in DB
        self.env.cr.execute(
            "SELECT count(*) FROM project_task_embedding WHERE task_id = %s",
            (task.id,)
        )
        count = self.env.cr.fetchone()[0]
        self.assertEqual(count, 1, "There should be one embedding record for the task")

        # Now update the task description and verify write triggers another job scheduling
        task.write({'description': '<p>Updated description with pgvector HNSW index</p>'})

        crons_after_write = self.env['ir.cron'].search([
            ('model_id.model', '=', 'project.task'),
            ('code', '=', f"model._generate_embedding({task.id})"),
            ('active', '=', True)
        ])
        self.assertTrue(crons_after_write, "A cron job should be scheduled after task write")

    def test_02_duplicate_wizard_similarity(self):
        """Test similarity search in the wizard"""
        # Create three tasks: two similar and one completely different
        task1 = self.env['project.task'].create({
            'name': 'User login authentication issues with LDAP',
            'description': '<p>LDAP integration is failing with timeouts on login page</p>',
            'project_id': self.project.id,
        })
        task2 = self.env['project.task'].create({
            'name': 'LDAP user authentication failure',
            'description': '<p>Login page times out during LDAP authentication check</p>',
            'project_id': self.project.id,
        })
        task3 = self.env['project.task'].create({
            'name': 'Write marketing content for social media',
            'description': '<p>Draft weekly blog post and publish to Twitter/LinkedIn</p>',
            'project_id': self.project.id,
        })

        # Generate embeddings synchronously
        task1._generate_embedding(task1.id)
        task2._generate_embedding(task2.id)
        task3._generate_embedding(task3.id)

        # Open duplicate detection wizard for task1
        action = task1.action_detect_duplicates()
        self.assertEqual(action['res_model'], 'project.task.duplicate.wizard')

        wizard = self.env['project.task.duplicate.wizard'].browse(action['res_id'])
        wizard.threshold = 0.1
        wizard._populate_duplicate_lines()

        # Read duplicate candidates
        lines = wizard.line_ids
        self.assertTrue(lines, "There should be similar tasks found")

        # The most similar task should be task2
        most_similar_task = lines[0].task_id
        self.assertEqual(most_similar_task.id, task2.id, "LDAP task should be identified as the most similar")

        # Verify action_open_task on the first line works as expected
        open_action = lines[0].action_open_task()
        self.assertEqual(open_action['res_model'], 'project.task')
        self.assertEqual(open_action['res_id'], task2.id)
        self.assertEqual(open_action['view_mode'], 'form')

        # Verify the completely different task is ranked lower or below threshold
        wizard.threshold = 0.6
        wizard._populate_duplicate_lines()
        high_similarity_tasks = wizard.line_ids.mapped('task_id')
        self.assertNotIn(task3, high_similarity_tasks, "Completely different task should not be listed with threshold 0.6")

    def test_03_wizard_onchange(self):
        """Test the onchange behaviors of the duplicate task wizard"""
        task1 = self.env['project.task'].create({
            'name': 'Configure mail SMTP settings',
            'description': '<p>Setup SMTP host, port, and credentials in the settings menu</p>',
            'project_id': self.project.id,
        })
        task2 = self.env['project.task'].create({
            'name': 'Mail server SMTP configuration',
            'description': '<p>Configure SMTP outgoing server credentials, host, and port</p>',
            'project_id': self.project.id,
        })

        # Generate embeddings
        task1._generate_embedding(task1.id)
        task2._generate_embedding(task2.id)

        # Create wizard for task1
        wizard = self.env['project.task.duplicate.wizard'].create({
            'task_id': task1.id,
            'top_k': 5,
            'threshold': 0.9,  # High threshold, should find 0 duplicates
        })

        self.assertEqual(len(wizard.line_ids), 0, "No duplicates should be found with a 0.9 threshold")

        # Simulate user changing threshold to 0.1 via onchange
        wizard.threshold = 0.1
        wizard._onchange_parameters()
        self.assertGreater(len(wizard.line_ids), 0, "Changing threshold to 0.1 via onchange should find duplicates")
