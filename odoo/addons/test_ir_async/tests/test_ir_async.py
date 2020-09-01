# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from odoo.tests import TransactionCase
from odoo.tools import mute_logger
from odoo.addons.base.models.ir_async import IrAsync, _logger as ir_async_logger
from odoo.addons.test_ir_async.models import TestIrAsyncModel

class TestIrAsync(TransactionCase):
    def setUp(self):
        super().setUp()
        TestIrAsyncModel.call_count = 0
        self.model = self.env['test_ir_async']
        self.dummy = self.model.create({"name": "dummy"})

    def execute(self, jobid):
        job = self.env['ir.async'].browse([jobid]).read(load=False)[0]
        IrAsync._process_job(self.cr, job)
        return job['payload']

    def test_call(self):
        job = self.env['ir.async'].call(self.dummy.swap_name)
        res = self.execute(job.id)
        self.assertEqual(res, False)
        self.assertEqual(TestIrAsyncModel.call_count, 1)
        self.assertEqual(self.dummy.name, "DUMMY")

    def test_model_call(self):
        job = self.env['ir.async'].call(self.model.echo_model, 1, 2, 3, d=4, f=6)
        res = self.execute(job.id)
        self.assertEqual(res, {"result": (1, 2, 3, 4, 5, {"f": 6})})
        self.assertEqual(TestIrAsyncModel.call_count, 1)

    def test_recursive_echo(self):
        jobid = self.env['ir.async'].call(self.model.async_echo, count=3).id
        for i in range(3):
            res = self.execute(jobid)
            jobid = res["result"]

        res = self.execute(jobid)
        self.assertEqual(TestIrAsyncModel.call_count, 5)
        self.assertEqual(res, {"result": (1, 2, 3, 4, 5, {})})

    def test_exception(self):
        job = self.env['ir.async'].call(self.model.annoying_cosmic_ray)
        with self.assertLogs(ir_async_logger, logging.ERROR) as cm:
            res = self.execute(job.id)
            self.assertEqual(len(cm.records), 1)
            self.assertEqual(cm.records[0].levelno, logging.ERROR)
            self.assertRegex(
                "".join(cm.output[0].splitlines()),
                r".*?".join([
                    r"Traceback \(most recent call last\):",
                    r"Traceback of async job \(most recent call last\):",
                    "A cosmic ray fucked up the system"
                ])
            )

        res_template = {
            'code': 200,
            'message': "Odoo Server Error",
            'data': {
                'name': 'builtins.ValueError',
                'message': 'A cosmic ray fucked up the system',
            }
        }

        res_error = {
            'code': res['error']['code'],
            'message': res['error']['message'],
            'data': {
                'name': res['error']['data']['name'],
                'message': res['error']['data']['message'],
            }
        }

        self.assertEqual(TestIrAsyncModel.call_count, 1)
        self.assertEqual(res_template, res_error)

    def test_user_error(self):
        job = self.env['ir.async'].call(self.model.faulty_layer_8)
        with self.assertLogs(ir_async_logger, logging.WARNING) as cm:
            res = self.execute(job.id)
            self.assertEqual(len(cm.records), 1)
            self.assertEqual(cm.records[0].levelno, logging.WARNING)
            self.assertNotIn("Traceback (most recent call last):", cm.output[0])
            self.assertIn("Bad bad bad user", cm.output[0])

        res_template = {
            'code': 200,
            'message': "Odoo Server Error",
            'data': {
                'name': 'odoo.exceptions.UserError',
                'message': 'Bad bad bad user',
            }
        }

        res_error = {
            'code': res['error']['code'],
            'message': res['error']['message'],
            'data': {
                'name': res['error']['data']['name'],
                'message': res['error']['data']['message'],
            }
        }

        self.assertEqual(TestIrAsyncModel.call_count, 1)
        self.assertEqual(res_template, res_error)

    def test_recursive_error(self):
        jobid = self.env['ir.async'].call(self.model.async_cosmic_ray, count=3).id
        for i in range(3):
            res = self.execute(jobid)
            jobid = res["result"]

        with self.assertLogs(ir_async_logger, logging.ERROR) as cm:
            res = self.execute(jobid)
            self.assertEqual(len(cm.records), 1)
            self.assertEqual(cm.records[0].levelno, logging.ERROR)
            self.assertRegex(
                "".join(cm.output[0].splitlines()),
                r".*?".join([
                    r"Traceback \(most recent call last\):",
                    r"Traceback of async job \(most recent call last\):",
                    r"Traceback of async job \(most recent call last\):",
                    r"Traceback of async job \(most recent call last\):",
                    r"Traceback of async job \(most recent call last\):",
                    "A cosmic ray fucked up the system"
                ])
            )

        res_template = {
            'code': 200,
            'message': "Odoo Server Error",
            'data': {
                'name': 'builtins.ValueError',
                'message': 'A cosmic ray fucked up the system',
            }
        }

        res_error = {
            'code': res['error']['code'],
            'message': res['error']['message'],
            'data': {
                'name': res['error']['data']['name'],
                'message': res['error']['data']['message'],
            }
        }

        self.assertEqual(TestIrAsyncModel.call_count, 5)
        self.assertEqual(res_template, res_error)

    def test_rollback(self):
        jobid = self.env['ir.async'].call(self.dummy.commit_raise).id
        with mute_logger(ir_async_logger.name):
            res = self.execute(jobid)
        self.assertEqual(self.dummy.name, 'dummy')
