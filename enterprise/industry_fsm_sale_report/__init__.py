# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def post_init(env):
    fsm_product = env.ref("industry_fsm.field_service_product", raise_if_not_found=False)
    if fsm_product:
        fsm_product.write(
            {"worksheet_template_id": env.ref("industry_fsm_report.fsm_worksheet_template").id, }
        )
