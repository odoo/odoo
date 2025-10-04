import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandRegistry = registry.category("discuss.channel_commands");

commandRegistry
    .add("help", {
        isAvailable: (store, thread) => store.self.type === "partner",
        help: _t("Show a helper message"),
        methodName: "execute_command_help",
    })
    .add("leave", {
        isAvailable: (store, thread) => store.self.type === "partner",
        help: _t("Leave this channel"),
        methodName: "execute_command_leave",
    })
    .add("who", {
        isAvailable: (store, thread) =>
            store.self.type === "partner" &&
            ["channel", "chat", "group"].includes(thread.channel_type),
        help: _t("List users in the current channel"),
        methodName: "execute_command_who",
    });
