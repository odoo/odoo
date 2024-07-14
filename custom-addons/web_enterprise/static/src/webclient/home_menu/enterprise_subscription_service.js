/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { browser } from "@web/core/browser/browser";
import { deserializeDateTime, serializeDate, formatDate } from "@web/core/l10n/dates";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ExpirationPanel } from "./expiration_panel";
import { cookie } from "@web/core/browser/cookie";

const { DateTime } = luxon;
import { Component, xml, useState } from "@odoo/owl";

function daysUntil(datetime) {
    const duration = datetime.diff(DateTime.utc(), "days");
    return Math.round(duration.values.days);
}

export class SubscriptionManager {
    constructor(env, { rpc, orm, notification }) {
        this.env = env;
        this.rpc = rpc;
        this.orm = orm;
        this.notification = notification;
        if (session.expiration_date) {
            this.expirationDate = deserializeDateTime(session.expiration_date);
        } else {
            // If no date found, assume 1 month and hope for the best
            this.expirationDate = DateTime.utc().plus({ days: 30 });
        }
        this.expirationReason = session.expiration_reason;
        // Hack: we need to know if there is at least one app installed (except from App and
        // Settings). We use mail to do that, as it is a dependency of almost every addon. To
        // determine whether mail is installed or not, we check for the presence of the key
        // "notification_type" in session_info, as it is added in mail for internal users.
        this.hasInstalledApps = "notification_type" in session;
        // "user" or "admin"
        this.warningType = session.warning;
        this.lastRequestStatus = null;
        this.isWarningHidden = cookie.get("oe_instance_hide_panel");
    }

    get formattedExpirationDate() {
        return formatDate(this.expirationDate, { format: "DDD" });
    }

    get daysLeft() {
        return daysUntil(this.expirationDate);
    }

    get unregistered() {
        return ["trial", "demo", false].includes(this.expirationReason);
    }

    hideWarning() {
        // Hide warning for 24 hours.
        cookie.set("oe_instance_hide_panel", true, 24 * 60 * 60);
        this.isWarningHidden = true;
    }

    async buy() {
        const limitDate = serializeDate(DateTime.utc().minus({ days: 15 }));
        const args = [
            [
                ["share", "=", false],
                ["login_date", ">=", limitDate],
            ],
        ];
        const nbUsers = await this.orm.call("res.users", "search_count", args);
        browser.location = `https://www.odoo.com/odoo-enterprise/upgrade?num_users=${nbUsers}`;
    }
    /**
     * Save the registration code then triggers a ping to submit it.
     */
    async submitCode(enterpriseCode) {
        const [oldDate, ] = await Promise.all([
            this.orm.call("ir.config_parameter", "get_param", ["database.expiration_date"]),
            this.orm.call("ir.config_parameter", "set_param", [
                "database.enterprise_code",
                enterpriseCode,
            ])
        ]);

        await this.orm.call("publisher_warranty.contract", "update_notification", [[]]);

        const [linkedSubscriptionUrl, linkedEmail, expirationDate] = await Promise.all([
            this.orm.call("ir.config_parameter", "get_param", [
                "database.already_linked_subscription_url",
            ]),
            this.orm.call("ir.config_parameter", "get_param", ["database.already_linked_email"]),
            this.orm.call("ir.config_parameter", "get_param", [
                "database.expiration_date",
            ])
        ]);

        if (linkedSubscriptionUrl) {
            this.lastRequestStatus = "link";
            this.linkedSubscriptionUrl = linkedSubscriptionUrl;
            this.mailDeliveryStatus = null;
            this.linkedEmail = linkedEmail;
        } else if (expirationDate !== oldDate) {
            this.lastRequestStatus = "success";
            this.expirationDate = deserializeDateTime(expirationDate);
            if (this.daysLeft > 30) {
                this.notification.add(
                    _t(
                        "Thank you, your registration was successful! Your database is valid until %s.",
                        this.formattedExpirationDate
                    ),
                    { type: "success" }
                );
            }
        } else {
            this.lastRequestStatus = "error";
        }
    }

    async checkStatus() {
        await this.orm.call("publisher_warranty.contract", "update_notification", [[]]);

        const expirationDateStr = await this.orm.call("ir.config_parameter", "get_param", [
            "database.expiration_date",
        ]);
        this.lastRequestStatus = "update";
        this.expirationDate = deserializeDateTime(expirationDateStr);
    }

    async sendUnlinkEmail() {
        const sendUnlinkInstructionsUrl = await this.orm.call("ir.config_parameter", "get_param", [
            "database.already_linked_send_mail_url",
        ]);
        this.mailDeliveryStatus = "ongoing";
        const { result, reason } = await this.rpc(sendUnlinkInstructionsUrl);
        if (result) {
            this.mailDeliveryStatus = "success";
        } else {
            this.mailDeliveryStatus = "fail";
            this.mailDeliveryStatusError = reason;
        }
    }

    async renew() {
        const enterpriseCode = await this.orm.call("ir.config_parameter", "get_param", [
            "database.enterprise_code",
        ]);

        const url = "https://www.odoo.com/odoo-enterprise/renew";
        const contractQueryString = enterpriseCode ? `?contract=${enterpriseCode}` : "";
        browser.location = `${url}${contractQueryString}`;
    }

    async upsell() {
        const limitDate = serializeDate(DateTime.utc().minus({ days: 15 }));
        const [enterpriseCode, nbUsers] = await Promise.all([
            this.orm.call("ir.config_parameter", "get_param", ["database.enterprise_code"]),
            this.orm.call("res.users", "search_count", [
                [
                    ["share", "=", false],
                    ["login_date", ">=", limitDate],
                ],
            ]),
        ]);
        const url = "https://www.odoo.com/odoo-enterprise/upsell";
        const contractQueryString = enterpriseCode ? `&contract=${enterpriseCode}` : "";
        browser.location = `${url}?num_users=${nbUsers}${contractQueryString}`;
    }
}

class ExpiredSubscriptionBlockUI extends Component {
    setup() {
        this.subscription = useState(useService("enterprise_subscription"));
    }
}
ExpiredSubscriptionBlockUI.props = {};
ExpiredSubscriptionBlockUI.template = xml`
<t t-if="subscription.daysLeft &lt;= 0">
    <div class="o_blockUI"/>
    <div style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 1100" class="d-flex align-items-center justify-content-center">
        <ExpirationPanel/>
    </div>
</t>`;
ExpiredSubscriptionBlockUI.components = { ExpirationPanel };

export const enterpriseSubscriptionService = {
    name: "enterprise_subscription",
    dependencies: ["orm", "rpc", "notification"],
    start(env, { rpc, orm, notification }) {
        registry
            .category("main_components")
            .add("expired_subscription_block_ui", { Component: ExpiredSubscriptionBlockUI });
        return new SubscriptionManager(env, { rpc, orm, notification });
    },
};

registry.category("services").add("enterprise_subscription", enterpriseSubscriptionService);
