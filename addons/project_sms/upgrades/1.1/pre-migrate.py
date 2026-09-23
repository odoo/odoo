import logging

from odoo.addons.base.models.ir_access_convert import rewrite_converted_domain

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    rewrite_converted_domain(
        cr,
        "project_sms",
        "ir_rule_sms_template_project_manager",
        "[('model', 'in', ('project.task', 'project.project'))]",
        "[('model_id.model', 'in', ('project.task.type', 'project.project.stage'))]",
        logger=_logger,
    )
