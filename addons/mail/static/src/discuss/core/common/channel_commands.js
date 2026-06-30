import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

commandRegistry
    .add("help", {
        condition: ({ store, thread }) => store.self_partner && !store.self.main_user_id.share,
        help: _t("Show a helper message"),
        methodName: "execute_command_help",
    })
    .add("leave", {
        condition: ({ store, thread }) => store.self_partner && !store.self.main_user_id.share,
        help: _t("Leave this channel"),
        methodName: "execute_command_leave",
    })
    .add("who", {
        condition: ({ store, thread }) => store.self_partner && !store.self.main_user_id.share,
        channel_types: ["channel", "chat", "group"],
        help: _t("List users in the current channel"),
        methodName: "execute_command_who",
    });
