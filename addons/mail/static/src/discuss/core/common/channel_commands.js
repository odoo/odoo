import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

commandRegistry
    .add("help", {
        help: _t("Show a helper message"),
        methodName: "execute_command_help",
    })
    .add("leave", {
        help: _t("Leave this channel"),
        methodName: "execute_command_leave",
        /** @param {import("models").DiscussChannel} channel */
        onExecute(channel) {
            channel.chatWindow?.close();
        },
    })
    .add("who", {
        channel_types: ["channel", "chat", "group"],
        help: _t("List users in the current channel"),
        methodName: "execute_command_who",
    });
