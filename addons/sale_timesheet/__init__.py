from . import controllers
from . import models
from . import wizards
from . import reports


def uninstall_hook(env):
    env.ref("account.account_analytic_line_rule_billing_user").write(
        {"operation": "cud", "domain": False}
    )
    env.ref("account.account_analytic_line_rule_readonly_user").write({"domain": False})


def _sale_timesheet_post_init(env):
    products = env["product.template"].search(
        [
            ("type", "=", "service"),
            (
                "service_tracking",
                "in",
                ["no", "task_global_project", "task_in_project", "project_only"],
            ),
            ("invoice_policy", "=", "ordered"),
            ("service_type", "=", "manual"),
        ]
    )

    for product in products:
        product.service_type = "timesheet"
        product._compute_service_policy()
