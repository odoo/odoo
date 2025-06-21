/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("discuss.channel_commands").add("history", {
    channel_types: ["livechat"],
    help: _t("See 15 last visited pages"),
    methodName: "execute_command_history",
});
