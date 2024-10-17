# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from .models.model import (
    TestModel, TestModelExposed, TestModelMultiWebsite, TestSubmodel,
    TestTag, Website,
)
from .models.res_config_settings import ResConfigSettings
