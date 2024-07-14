/* @odoo-module */

import { Messaging } from "@mail/core/common/messaging_service";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

patch(Messaging.prototype, {
    initMessagingCallback(data) {
        super.initMessagingCallback(data);
        if ("helpdesk_livechat_active" in data) {
            this.store.helpdesk_livechat_active = data.helpdesk_livechat_active;
        }
        if (this.store.helpdesk_livechat_active) {
            registry
                .category("discuss.channel_commands")
                .add(
                    "ticket",
                    {
                        help: _t("Create a new helpdesk ticket (/ticket ticket title)"),
                        methodName: "execute_command_helpdesk",
                    },
                    { force: true }
                )
                .add(
                    "search_tickets",
                    {
                        force: true,
                        help: _t("Search helpdesk tickets (/search_tickets keyword)"),
                        methodName: "execute_command_helpdesk_search",
                    },
                    { force: true }
                );
        } else {
            registry.category("discuss.channel_commands").remove("ticket");
            registry.category("discuss.channel_commands").remove("search_tickets");
        }
    },
});
