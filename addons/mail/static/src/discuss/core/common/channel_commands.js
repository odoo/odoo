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
        /** @param {import("models").DiscussChannel} channel */
        async onExecute(channel) {
            await channel.leaveChannel();
        },
    })
    .add("who", {
        channel_types: ["channel", "chat", "group"],
        help: _t("List users in the current channel"),
        methodName: "execute_command_who",
    });
