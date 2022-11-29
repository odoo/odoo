/* @odoo-module */

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

const commandRegistry = registry.category("mail.channel_commands");

commandRegistry
    .add("help", {
        help: _lt("Show a helper message"),
        methodName: "execute_command_help",
    })
    .add("leave", {
        help: _lt("Leave this channel"),
        methodName: "execute_command_leave",
    })
    .add("who", {
        channel_types: ["channel", "chat", "group"],
        help: _lt("List users in the current channel"),
        methodName: "execute_command_who",
    });
