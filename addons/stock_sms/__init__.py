from . import models
from . import wizards


def _update_default_sms_template(env):
    company_ids_without_default_sms_template_id = env["res.company"].search(
        [("stock_config_id.stock_sms_confirmation_template_id", "=", False)]
    )
    default_sms_template_id = env.ref(
        "stock_sms.sms_template_data_stock_delivery", raise_if_not_found=False
    )
    if default_sms_template_id:
        company_ids_without_default_sms_template_id.write(
            {
                "stock_text_confirmation": True,
                "stock_sms_confirmation_template_id": default_sms_template_id.id,
            }
        )


def _reset_sms_text_confirmation(env):
    company_ids_with_sms_text_confirmation = env["res.company"].search(
        [
            ("stock_config_id.stock_text_confirmation", "=", True),
            ("stock_config_id.stock_confirmation_type", "=", "sms"),
        ]
    )
    company_ids_with_sms_text_confirmation.write(
        {
            "stock_text_confirmation": False,
        }
    )
