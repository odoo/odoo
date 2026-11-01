# -*- coding: utf-8 -*-
"""Port checks for the legacy ``dtr_advance`` Jasper reports.

Four printable reports/foms are ported from the Odoo 15 ``dtr_advance``
module:

* ``dtr.adv.request.form``                      (f_adv_001)
* ``dtr.adv.clear.form``                        (f_adv_002)
* ``dtr.adv.request.condition.report``          (r_adv_001)
* ``dtr.adv.request.at.date.report``            (r_adv_002)

Every wizard re-uses the shared engine (``od19.jasper.report``), so these
tests assert the models are registered and that the compiled ``.jasper``
templates ship with the module on disk.
"""
import os

from odoo.tests import tagged, TransactionCase

# model -> (description, compiled template name)
MODELS = {
    "dtr.adv.request.form": ("Advance Request Form", "dtr_adv_request_form.jasper"),
    "dtr.adv.clear.form": ("Advance Clear Form", "dtr_adv_clear_form.jasper"),
    "dtr.adv.request.condition.report": (
        "Advance Request Condition Report",
        "dtr_adv_request_condition_report.jasper",
    ),
    "dtr.adv.request.at.date.report": (
        "Advance Request At Date Report",
        "dtr_adv_request_at_date_report.jasper",
    ),
}


@tagged("post_install", "-at_install")
class TestAdvancePorts(TransactionCase):
    def test_models_are_registered(self):
        for model, (description, _jasper) in MODELS.items():
            report = self.env[model]
            self.assertEqual(report._name, model)
            self.assertEqual(report._description, description)
            self.assertEqual(list(report._inherit), ["od19.jasper.report"])

    def test_compiled_templates_are_shipped(self):
        for model, (_description, jasper) in MODELS.items():
            report = self.env[model].create({})
            self.assertTrue(report.jasper_file.endswith(jasper), report.jasper_file)
            self.assertTrue(os.path.isfile(report.jasper_file), report.jasper_file)
