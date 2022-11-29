/** @odoo-module */

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("mail.channel_commands").add("lead", {
    help: _lt("Create a new lead (/lead lead title)"),
    methodName: "execute_command_lead",
});
