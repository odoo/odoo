# Copyright 2015-2016 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html)

# pylint: disable=odoo-addons-relative-import
# we are testing, we want to test as we were an external consumer of the API
from odoo.addons.queue_job.jobrunner import runner

from .common import load_doctests

load_tests = load_doctests(runner)
