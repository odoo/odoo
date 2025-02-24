import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

commandRegistry
    .add("help", {
        help: _t("Show a helper message"),
        icon: "fa-info",
        methodName: "execute_command_help",
    })
    .add("leave", {
        help: _t("Leave this channel"),
        icon: "fa-sign-out",
        methodName: "execute_command_leave",
    })
    .add("who", {
        channel_types: ["channel", "chat", "group"],
        help: _t("List users in the current channel"),
        icon: "fa-users",
        methodName: "execute_command_who",
    });
