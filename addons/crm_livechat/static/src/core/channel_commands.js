/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("discuss.channel_commands").add("lead", {
    help: _t("Create a new lead (/lead lead title)"),
    methodName: "execute_command_lead",
});
