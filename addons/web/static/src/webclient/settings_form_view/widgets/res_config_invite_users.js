import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { unique } from "@web/core/utils/arrays";
import { useService } from "@web/core/utils/hooks";

import { Component, useState, onWillStart } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

class ResConfigInviteUsers extends Component {
    static template = "res_config_invite_users";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.invite = useService("user_invite");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            status: "idle", // idle, inviting
            emails: "",
            invite: null,
        });

        onWillStart(async () => {
            this.state.invite = await this.invite.fetchData();
        });
    }

    /**
     * @param {string} email
     * @returns {boolean} true if the given email address is valid
     */
    validateEmail(email) {
        const re =
            /^([a-z0-9][-a-z0-9_+.]*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,63}(?:\.[a-z]{2})?)$/i;
        return re.test(email);
    }

    get emails() {
        return unique(
            this.state.emails
                .split(/[ ,;\n]+/)
                .map((email) => email.trim())
                .filter((email) => email.length)
        );
    }

    validate() {
        if (!this.emails.length) {
            throw new Error(_t("Empty email address"));
        }
        const invalidEmails = [];
        for (const email of this.emails) {
            if (!this.validateEmail(email)) {
                invalidEmails.push(email);
            }
        }
        if (invalidEmails.length) {
            const errorMessage = (() => {
                switch (invalidEmails.length) {
                    case 1:
                        return _t("Invalid email address: %(address)s", {
                            address: invalidEmails[0],
                        });
                    case 2:
                        return _t("Invalid email addresses: %(two_addresses)s", {
                            two_addresses: invalidEmails,
                        });
                    default:
                        return _t("Invalid email addresses: %(addresses)s", {
                            addresses: invalidEmails,
                        });
                }
            })();
            throw new Error(errorMessage);
        }
    }

    get inviteButtonText() {
        if (this.state.status === "inviting") {
            return _t("Inviting...");
        }
        return _t("Invite");
    }

    onClickMore(ev) {
        this.action.doAction(this.state.invite.action_pending_users);
    }

    onClickUser(ev, user) {
        const action = Object.assign({}, this.state.invite.action_pending_users, {
            res_id: user[0],
        });
        this.action.doAction(action);
    }

    onKeydownUserEmails(ev) {
        const keys = ["Enter", "Tab", ","];
        if (keys.includes(ev.key)) {
            if (ev.key === "Tab" && !this.emails.length) {
                return;
            }
            ev.preventDefault();
            this.sendInvite();
        }
    }

    /**
     * Send invitation for valid and unique email addresses
     *
     * @private
     */
    async sendInvite() {
        try {
            this.validate();
        } catch (e) {
            this.notification.add(e.message, { type: "danger" });
            return;
        }

        this.state.status = "inviting";

        const pendingUserEmails = this.state.invite.pending_users.map((user) => user[1]);
        const emailsLeftToProcess = this.emails.filter(
            (email) => !pendingUserEmails.includes(email)
        );

        try {
            if (emailsLeftToProcess) {
                await this.orm.call("res.users", "web_create_users", [emailsLeftToProcess]);
                this.state.invite = await this.invite.fetchData(true);
            }
        } finally {
            this.state.emails = "";
            this.state.status = "idle";
        }
    }
}

export const resConfigInviteUsers = {
    component: ResConfigInviteUsers,
};

registry.category("view_widgets").add("res_config_invite_users", resConfigInviteUsers);
