import contextlib
import datetime
import logging
from ast import literal_eval

from odoo import SUPERUSER_ID, api, fields, release
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.models import AbstractModel
from odoo.tools import cloc, config
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class Publisher_WarrantyContract(AbstractModel):
    _name = "publisher_warranty.contract"
    _description = "Publisher Warranty Contract"

    @api.model
    def _get_message(self) -> dict:
        Users = self.env["res.users"]
        IrParamSudo = self.env["ir.config_parameter"].sudo()

        dbuuid = IrParamSudo.get_param("database.uuid")
        db_create_date = IrParamSudo.get_param("database.create_date")
        limit_date = fields.Datetime.now() - datetime.timedelta(15)
        nbr_users = Users.search_count([("active", "=", True)])
        nbr_active_users = Users.search_count(
            [("login_date", ">=", limit_date), ("active", "=", True)]
        )
        nbr_share_users = 0
        nbr_active_share_users = 0
        if "share" in Users._fields:
            nbr_share_users = Users.search_count(
                [("share", "=", True), ("active", "=", True)]
            )
            nbr_active_share_users = Users.search_count(
                [
                    ("share", "=", True),
                    ("login_date", ">=", limit_date),
                    ("active", "=", True),
                ]
            )
        user = self.env.user
        domain = [
            ("application", "=", True),
            ("state", "in", ["installed", "to upgrade", "to remove"]),
        ]
        apps = self.env["ir.module.module"].sudo().search_read(domain, ["name"])

        enterprise_code = IrParamSudo.get_param("database.enterprise_code")

        web_base_url = IrParamSudo.get_param("web.base.url")
        msg = {
            "dbuuid": dbuuid,
            "nbr_users": nbr_users,
            "nbr_active_users": nbr_active_users,
            "nbr_share_users": nbr_share_users,
            "nbr_active_share_users": nbr_active_share_users,
            "dbname": self.env.cr.dbname,
            "db_create_date": db_create_date,
            "version": release.version,
            "language": user.lang,
            "web_base_url": web_base_url,
            "apps": [app["name"] for app in apps],
            "enterprise_code": enterprise_code,
        }
        if user.partner_id.company_id:
            company_id = user.partner_id.company_id
            msg.update(
                {
                    "name": company_id.name,
                    "email": company_id.email,
                    "phone": company_id.phone_ids._primary().number,
                }
            )
        if not IrParamSudo.get_param_bool("publisher_warranty.maintenance_disable"):
            msg["maintenance"] = self._get_maintenance()
            IrParamSudo.set_param("publisher_warranty.cloc", str(msg["maintenance"]))
        return msg

    @api.model
    def _get_maintenance(self) -> dict:
        maintenance = {"version": cloc.VERSION}
        try:
            counter = cloc.Cloc()
            counter.count_env(self.env)
            if counter.code:
                maintenance["modules"] = counter.code
            if counter.errors:
                maintenance["errors"] = list(counter.errors.keys())
        except Exception:
            _logger.exception("cloc collection failed")
            maintenance["errors"] = ["cloc/error"]
        return maintenance

    @api.model
    def _get_verbose_maintenance(self) -> dict:
        counter = cloc.Cloc()
        counter.count_env(self.env)
        return {
            "modules_count": counter.modules,
            "modules_excluded": counter.excluded,
        }

    @api.model
    def _get_sys_logs(self) -> dict:
        msg = self._get_message()
        arguments = {"arg0": str(msg), "action": "update"}

        url = config.get("publisher_warranty_url")

        r = self.env["ir.egress"].request(
            "POST",
            url,
            purpose="publisher_warranty",
            policy="private",
            data=arguments,
            timeout=30,
        )
        r.raise_for_status()
        return literal_eval(r.text)

    def update_notification(self, cron_mode: bool = True) -> bool:
        try:
            try:
                with _debug.perf("publisher_warranty_contacted", cron=cron_mode):
                    result = self._get_sys_logs()
            except Exception as error:
                _debug.logic("publisher_warranty_failed", error=type(error).__name__)
                if cron_mode:
                    return False
                _logger.debug("Exception while sending a get logs messages", exc_info=1)
                raise UserError(
                    _("Error during communication with the publisher warranty server.")
                ) from None
            user = self.env["res.users"].sudo().browse(SUPERUSER_ID)
            poster = self.sudo().env.ref(
                "mail.channel_all_employees", raise_if_not_found=False
            )
            _debug.pipeline(
                "update_notification",
                messages=len(result.get("messages", ())),
                poster=poster.id if poster else None,
                enterprise_info=bool(result.get("enterprise_info")),
            )
            for message in result.get("messages", ()) if poster else ():
                with contextlib.suppress(Exception):
                    poster.message_post(
                        body=message,
                        subtype_xmlid="mail.mt_comment",
                        partner_ids=[user.partner_id.id],
                    )
            if result.get("enterprise_info"):
                set_param = self.env["ir.config_parameter"].sudo().set_param
                set_param(
                    "database.expiration_date",
                    result["enterprise_info"].get("expiration_date"),
                )
                set_param(
                    "database.expiration_reason",
                    result["enterprise_info"].get("expiration_reason", "trial"),
                )
                set_param(
                    "database.enterprise_code",
                    result["enterprise_info"].get("enterprise_code"),
                )
                set_param(
                    "database.already_linked_subscription_url",
                    result["enterprise_info"].get(
                        "database_already_linked_subscription_url"
                    ),
                )
                set_param(
                    "database.already_linked_email",
                    result["enterprise_info"].get("database_already_linked_email"),
                )
                set_param(
                    "database.already_linked_send_mail_url",
                    result["enterprise_info"].get(
                        "database_already_linked_send_mail_url"
                    ),
                )

        except Exception:
            if cron_mode:
                return False
            else:
                raise
        return True
