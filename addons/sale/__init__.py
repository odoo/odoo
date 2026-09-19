from odoo.tools.misc import str2bool

from . import const
from . import controllers
from . import models
from . import reports
from . import wizards


def _post_init_hook(env):
    _sync_crons(env)
    _setup_downpayment_account(env)


def _sync_crons(env):
    for param, cron_xmlid in const.PARAM_CRON_MAPPING.items():
        if cron := env.ref(cron_xmlid, raise_if_not_found=False):
            cron.active = str2bool(env["ir.config_parameter"].get_param(param, "False"))


def _setup_downpayment_account(env):
    for company in env.companies:
        if not company.account_config_id.chart_template:
            continue

        template_data = (
            env["account.chart.template"]
            ._prepare_chart_template_data(company.account_config_id.chart_template)
            .get("template_data")
        )
        if template_data and template_data.get("downpayment_account_id"):
            property_downpayment_account = (
                env["account.chart.template"]
                .with_company(company)
                .ref(template_data["downpayment_account_id"], raise_if_not_found=False)
            )
            if property_downpayment_account:
                company.downpayment_account_id = property_downpayment_account
