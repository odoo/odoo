// @ts-check
/** @odoo-module native */

import { Component, markup, reactive, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { deserializeDateTime, formatDate, serializeDate } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";

import { ExpirationPanel } from "./expiration_panel.js";
import { SysAdminPanel } from "./sysadmin_panel.js";

import { DateTime } from "luxon";
/**
 * @param {DateTime} datetime
 * @returns {number}
 */
function daysUntil(datetime) {
    const duration = datetime.diff(DateTime.utc(), "days");
    return Math.round(duration.as("days"));
}

export class SubscriptionManager {
    /** @type {string | null} */
    lastRequestStatus = null;
    /** @type {boolean} */
    isWarningHidden = false;
    /** @type {string | undefined} */
    linkedSubscriptionUrl;
    /** @type {string | undefined} */
    linkedEmail;
    /** @type {string | null | undefined} */
    mailDeliveryStatus;
    /** @type {string | undefined} */
    mailDeliveryStatusError;

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ orm: any; notification: any }} services
     */
    constructor(env, { orm, notification }) {
        this.env = env;
        this.orm = orm;
        this.notification = notification;
        if (session.expiration_date) {
            this.expirationDate = deserializeDateTime(session.expiration_date);
        } else {
            this.expirationDate = DateTime.utc().plus({ days: 30 });
        }
        this.expirationReason = session.expiration_reason;
        this.hasInstalledApps = "storeData" in session;
        this.warningType = session.warning;
        this.isWarningHidden = Boolean(cookie.get("oe_instance_hide_panel"));
        this.sysadmin = session.sysadmin_message || {};
        if (this.sysadmin.message) {
            this.sysadmin.message = markup(this.sysadmin.message);
        }
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
        cookie.set("oe_instance_hide_panel", "1", 24 * 60 * 60);
        this.isWarningHidden = true;
    }

    /** @returns {Promise<number>} */
    _countRecentlyActiveUsers() {
        const limitDate = serializeDate(DateTime.utc().minus({ days: 15 }));
        return this.orm.call("res.users", "search_count", [
            [
                ["share", "=", false],
                ["login_date", ">=", limitDate],
            ],
        ]);
    }

    async buy() {
        const nbUsers = await this._countRecentlyActiveUsers();
        browser.location.href = `https://www.odoo.com/odoo-enterprise/upgrade?num_users=${nbUsers}`;
    }
    /** @param {string} enterpriseCode */
    async submitCode(enterpriseCode) {
        const [oldDate] = await Promise.all([
            this.orm.call("ir.config_parameter", "get_param", [
                "database.expiration_date",
            ]),
            this.orm.call("ir.config_parameter", "set_param", [
                "database.enterprise_code",
                enterpriseCode,
            ]),
        ]);

        await this.orm.call("publisher_warranty.contract", "update_notification", [[]]);

        const [linkedSubscriptionUrl, linkedEmail, expirationDate] = await Promise.all([
            this.orm.call("ir.config_parameter", "get_param", [
                "database.already_linked_subscription_url",
            ]),
            this.orm.call("ir.config_parameter", "get_param", [
                "database.already_linked_email",
            ]),
            this.orm.call("ir.config_parameter", "get_param", [
                "database.expiration_date",
            ]),
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
                        this.formattedExpirationDate,
                    ),
                    { type: "success" },
                );
            }
        } else {
            this.lastRequestStatus = "error";
        }
    }

    async checkStatus() {
        await this.orm.call("publisher_warranty.contract", "update_notification", [[]]);

        const expirationDateStr = await this.orm.call(
            "ir.config_parameter",
            "get_param",
            ["database.expiration_date"],
        );
        this.lastRequestStatus = "update";
        this.expirationDate = deserializeDateTime(expirationDateStr);
    }

    async sendUnlinkEmail() {
        const sendUnlinkInstructionsUrl = await this.orm.call(
            "ir.config_parameter",
            "get_param",
            ["database.already_linked_send_mail_url"],
        );
        this.mailDeliveryStatus = "ongoing";
        const { result, reason } = await rpc(sendUnlinkInstructionsUrl);
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
        browser.location.href = `${url}${contractQueryString}`;
    }

    async upsell() {
        const [enterpriseCode, nbUsers] = await Promise.all([
            this.orm.call("ir.config_parameter", "get_param", [
                "database.enterprise_code",
            ]),
            this._countRecentlyActiveUsers(),
        ]);
        const url = "https://www.odoo.com/odoo-enterprise/upsell";
        const contractQueryString = enterpriseCode ? `&contract=${enterpriseCode}` : "";
        browser.location.href = `${url}?num_users=${nbUsers}${contractQueryString}`;
    }
}

class ExpiredSubscriptionBlockUI extends Component {
    static props = {};
    static template = xml`
        <t t-if="this.subscription.daysLeft &lt;= 0">
            <div class="o_expired_subscription_overlay position-absolute top-0 start-0 end-0 bottom-0 d-flex align-items-center justify-content-center">
                <ExpirationPanel t-if="!this.subscription.sysadmin.replace"/>
                <!-- Only daysLeft and the message's existence belong here.
                     Who may SEE a message is showMessage's job: it already
                     tells the reader's level (warningType) apart from the
                     message's audience (sysadmin.warning_type). Repeating an
                     admin test here conflated the two and hid a user-audience
                     message from every non-admin reader exactly while the UI
                     was blocked. -->
                <SysAdminPanel t-if="this.subscription.sysadmin.message"/>
            </div>
        </t>`;
    static components = { ExpirationPanel, SysAdminPanel };
    setup() {
        this.subscription = useService("enterprise_subscription");
    }
}

registry.category("main_components").add("expired_subscription_block_ui", {
    Component: ExpiredSubscriptionBlockUI,
});

export const enterpriseSubscriptionService = {
    name: "enterprise_subscription",
    dependencies: ["orm", "notification"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {{ orm: any; notification: any }} services
     */
    start(env, { orm, notification }) {
        return reactive(new SubscriptionManager(env, { orm, notification }));
    },
};

registry
    .category("services")
    .add("enterprise_subscription", enterpriseSubscriptionService);
