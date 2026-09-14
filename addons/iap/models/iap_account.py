import hashlib
import logging
import secrets
import uuid
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.libs.web import urljoin as url_join
from odoo.modules import module
from odoo.tools import get_lang

from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger(__name__)


class IapAccount(models.Model):
    _name = "iap.account"
    _description = "IAP Account"

    name = fields.Char()
    service_id = fields.Many2one(
        comodel_name="iap.service",
        required=True,
    )
    service_name = fields.Char(related="service_id.technical_name")
    service_locked = fields.Boolean(
        default=False
    )  # If True, the service can't be edited anymore
    description = fields.Char(related="service_id.description")
    credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Token Credential",
        copy=False,
        ondelete="restrict",
        groups="base.group_system",
        help="Holds this account's token.",
    )
    account_token = fields.Char(
        compute="_compute_account_token",
        inverse="_inverse_account_token",
        default=lambda s: uuid.uuid4().hex,
        copy=False,
        groups="base.group_system",
        help="Account token is your authentication key for this service. Do not share it.",
    )
    company_ids = fields.Many2many(comodel_name="res.company")

    # Set from the IAP server when the view loads, except warning_user_ids, which
    # is local; both warning fields are pushed to IAP on write
    balance = fields.Char(readonly=True)
    warning_threshold = fields.Float(string="Email Alert Threshold")
    warning_user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Email Alert Recipients",
    )
    state = fields.Selection(
        selection=[
            ("banned", "Banned"),
            ("registered", "Registered"),
            ("unregistered", "Unregistered"),
        ],
        readonly=True,
    )

    @api.depends("credential_id")
    def _compute_account_token(self):
        for account in self:
            credential = account.sudo().credential_id
            account.account_token = (
                credential._use_secret("iap:account_token") if credential else False
            ) or False

    def _inverse_account_token(self):
        for account in self.sudo():
            token = account.account_token
            credential = account.credential_id
            if not token:
                account.credential_id = False
                credential.unlink()
            elif credential:
                credential.credential_value = token
            else:
                account.credential_id = (
                    self.env["credential.credential"]
                    .sudo()
                    .create(
                        {
                            "name": self.env._(
                                "IAP: %(service)s (account %(account)s)",
                                service=account.service_id.name or account.name,
                                account=account.id,
                            ),
                            "category_id": self.env.ref(
                                "credential.credential_category_custom"
                            ).id,
                            "credential_value": token,
                        }
                    )
                )

    @api.constrains("warning_threshold", "warning_user_ids")
    def check_warning_alerts(self):
        for account in self:
            if account.warning_threshold < 0:
                raise UserError(_("Please set a positive email alert threshold."))
            if (
                account.warning_threshold > 0
                and not account.warning_user_ids
                and not self.env.context.get("disable_iap_update")
            ):
                raise UserError(_("Please set at least one email alert recipient."))
            users_with_no_email = [
                user.name for user in account.warning_user_ids if not user.email
            ]
            if users_with_no_email:
                raise UserError(
                    _(
                        "One of the email alert recipients doesn't have an email address set. Users: %s",
                        ",".join(users_with_no_email),
                    )
                )

    def web_read(self, *args, **kwargs):
        if not self.env.context.get("disable_iap_fetch"):
            self._update_account_information_from_iap()
        return super().web_read(*args, **kwargs)

    def web_save(self, *args, **kwargs):
        return super(IapAccount, self.with_context(disable_iap_fetch=True)).web_save(
            *args, **kwargs
        )

    def write(self, vals):
        if "service_id" in vals and any(
            account.service_locked and account.service_id.id != vals["service_id"]
            for account in self
        ):
            raise UserError(_("You cannot change the service of a locked IAP account."))
        res = super().write(vals)
        if not self.env.context.get("disable_iap_update") and any(
            warning_attribute in vals
            for warning_attribute in ("warning_threshold", "warning_user_ids")
        ):
            route = "/iap/1/update-warning-email-alerts"
            endpoint = iap_tools.iap_get_endpoint(self.env)
            url = url_join(endpoint, route)
            # One blocking iap_jsonrpc round-trip per account: this endpoint's
            # contract takes a single account, unlike the batched
            # 'iap_accounts' list _update_account_information_from_iap sends in
            # one call. A bulk write across many accounts pays one network
            # round-trip per record inside this write() transaction.
            for account in self:
                data = {
                    "account_token": account.sudo().account_token,
                    "warning_threshold": account.warning_threshold,
                    "warning_emails": [
                        {
                            "email": user.email,
                            "lang_code": user.lang or get_lang(self.env).code,
                        }
                        for user in account.warning_user_ids
                    ],
                }
                try:
                    iap_tools.iap_jsonrpc(url=url, params=data, env=self.env)
                except AccessError as e:
                    _logger.warning(
                        "Update of the warning email configuration has failed: %s", e
                    )
        return res

    def _update_account_information_from_iap(self):
        # During testing, we don't want to call the iap server
        if module.current_test:
            return
        route = "/iap/1/get-accounts-information"
        endpoint = iap_tools.iap_get_endpoint(self.env)
        url = url_join(endpoint, route)
        params = {
            "iap_accounts": [
                {
                    "token": account.sudo().account_token,
                    "service": account.service_id.technical_name,
                }
                for account in self
                if account.service_id
            ],
            "dbuuid": self.env["ir.config_parameter"].sudo().get_param("database.uuid"),
        }
        try:
            accounts_information = iap_tools.iap_jsonrpc(
                url=url, params=params, env=self.env
            )
        except AccessError as e:
            _logger.warning("Fetch of the IAP accounts information has failed: %s", e)
            return

        for token, information in accounts_information.items():
            information.pop("link_to_service_page", None)
            accounts = self.filtered(
                lambda acc, token=token: secrets.compare_digest(
                    acc.sudo().account_token, token
                )
            )

            for account in accounts:
                # Round to a unit for integer services, to 4 decimals otherwise,
                # to avoid long decimals
                balance_amount = round(
                    information["balance"],
                    None if account.service_id.integer_balance else 4,
                )
                balance = f"{balance_amount} {account.service_id.unit_name or ''}"

                account_info = self._get_account_info(account, balance, information)
                account.with_context(
                    disable_iap_update=True, tracking_disable=True
                ).write(account_info)

    def _get_account_info(self, account, balance, information):
        return {
            "balance": balance,
            "warning_threshold": information["warning_threshold"],
            "state": information["registered"],
            "service_locked": True,  # The account exists on IAP, prevent editing its service
        }

    @api.model_create_multi
    def create(self, vals_list):
        accounts = super().create(vals_list)
        for account in accounts:
            if not account.name:
                account.name = account.service_id.name

        if self.env["ir.config_parameter"].sudo().get_param("database.is_neutralized"):
            # Disable new accounts on a neutralized database
            for account in accounts:
                account.account_token = (
                    f"{account.account_token.split('+')[0]}+disabled"
                )
        return accounts

    @api.model
    def get(self, service_name, force_create=True):
        domain = [
            ("service_name", "=", service_name),
            "|",
            ("company_ids", "in", self.env.companies.ids),
            ("company_ids", "=", False),
        ]
        accounts = self.search(domain, order="id desc")
        accounts_without_token = accounts.filtered(
            lambda acc: not acc.sudo().account_token
        )
        if accounts_without_token:
            with self.pool.cursor() as cr:
                # In case of a further error that will rollback the database, we should
                # use a different SQL cursor so the accounts deletion is not undone.

                # Flush the pending operations to avoid a deadlock.
                self.env.flush_all()
                IapAccount = self.with_env(self.env(cr=cr))
                # Need to use sudo because regular users do not have delete right
                IapAccount.search(
                    domain + [("credential_id", "=", False)]
                ).sudo().unlink()
                accounts -= accounts_without_token
        if not accounts:
            service = self.env["iap.service"].search(
                [("technical_name", "=", service_name)], limit=1
            )
            if not service:
                raise UserError(
                    self.env._("No service exists with the provided technical name")
                )
            if module.current_test:
                # During testing, we don't want to commit the creation of a new IAP account to the database
                return self.sudo().create({"service_id": service.id})

            with self.pool.cursor() as cr:
                # Since the account did not exist yet, we will encounter an
                # InsufficientCreditError, which is going to rollback the database and
                # undo the account creation, preventing the process to continue further.

                # Flush the pending operations to avoid a deadlock.
                self.env.flush_all()
                IapAccount = self.with_env(self.env(cr=cr))
                account = IapAccount.search(domain, order="id desc", limit=1)
                if not account:
                    if not force_create:
                        return account
                    account = IapAccount.create({"service_id": service.id})
                # fetch 'account_token' into cache with this cursor,
                # as self's cursor cannot see this account
                account_token = account.sudo().account_token
            account = self.browse(account.id)
            self.env.cache.set(
                account, IapAccount._fields["account_token"], account_token
            )
            return account
        accounts_with_company = accounts.filtered(lambda acc: acc.company_ids)
        if accounts_with_company:
            return accounts_with_company[0]
        return accounts[0]

    @api.model
    def get_account_id(self, service_name):
        return self.get(service_name).id

    @api.model
    def get_credits_url(self, service_name, account_token=None):
        """Called notably by: action_buy_credits, partner_autocomplete, snailmail, ..."""
        dbuuid = self.env["ir.config_parameter"].sudo().get_param("database.uuid")
        endpoint = iap_tools.iap_get_endpoint(self.env)
        route = "/iap/1/credit"
        base_url = url_join(endpoint, route)
        account_token = account_token or self.get(service_name).sudo().account_token
        hashed_account_token = self._hash_iap_token(account_token)
        d = {
            "dbuuid": dbuuid,
            "service_name": service_name,
            "account_token": hashed_account_token,
            "hashed": 1,
        }
        return "%s?%s" % (base_url, urlencode(d))

    @api.model
    def _hash_iap_token(self, key):
        # disregard possible suffix
        key = (key or "").split("+")[0]
        if not key:
            raise UserError(_("The IAP token provided is invalid or empty."))
        return hashlib.sha1(key.encode("utf-8")).hexdigest()

    def action_buy_credits(self):
        return {
            "type": "ir.actions.act_url",
            "url": self.env["iap.account"].get_credits_url(
                account_token=self.sudo().account_token,
                service_name=self.service_name,
            ),
        }

    @api.model
    def get_config_account_url(self):
        """Called notably by ajax partner_autocomplete."""
        account = self.env["iap.account"].get("partner_autocomplete")
        menu = self.env.ref("iap.iap_account_menu")
        if not self.env.user.has_group("base.group_no_one"):
            return False
        if account:
            url = f"/odoo/action-iap.iap_account_action/{account.id}?menu_id={menu.id}"
        else:
            url = f"/odoo/action-iap.iap_account_action?menu_id={menu.id}"
        return url

    @api.model
    def get_credits(self, service_name):
        account = self.get(service_name, force_create=False)
        credit = 0

        if account:
            route = "/iap/1/balance"
            endpoint = iap_tools.iap_get_endpoint(self.env)
            url = url_join(endpoint, route)
            params = {
                "dbuuid": self.env["ir.config_parameter"]
                .sudo()
                .get_param("database.uuid"),
                "account_token": account.sudo().account_token,
                "service_name": service_name,
            }
            try:
                credit = iap_tools.iap_jsonrpc(url=url, params=params, env=self.env)
            except AccessError as e:
                _logger.info("Get credit error : %s", e)
                credit = -1

        return credit
