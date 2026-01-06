# -*- coding: utf-8 -*-
"""
JOKER Queue Module Tests
"""
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "joker")
class TestJokerQueue(TransactionCase):
    """Test cases for JOKER Queue module"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Job = cls.env["joker.queue.job"]

    def test_job_creation(self):
        """Test queue job creation"""
        job = self.Job.create(
            {
                "name": "Test Job",
                "job_type": "sync",
                "priority": 10,
            }
        )
        self.assertTrue(job.id)
        self.assertEqual(job.state, "pending")

    def test_job_states(self):
        """Test job state transitions"""
        job = self.Job.create(
            {
                "name": "State Test Job",
                "job_type": "export",
                "priority": 5,
            }
        )

        # Check initial state
        self.assertEqual(job.state, "pending")

        # Simulate start
        job.write({"state": "running", "started_at": job.create_date})
        self.assertEqual(job.state, "running")

    def test_job_priorities(self):
        """Test job priority ordering"""
        high_priority = self.Job.create(
            {
                "name": "High Priority",
                "job_type": "sync",
                "priority": 1,
            }
        )
        low_priority = self.Job.create(
            {
                "name": "Low Priority",
                "job_type": "sync",
                "priority": 100,
            }
        )

        # High priority should have lower number
        self.assertLess(high_priority.priority, low_priority.priority)

    def test_job_retry_mechanism(self):
        """Test job retry count"""
        job = self.Job.create(
            {
                "name": "Retry Test",
                "job_type": "import",
                "priority": 10,
                "max_retries": 3,
            }
        )

        self.assertEqual(job.retry_count, 0)
        self.assertEqual(job.max_retries, 3)
