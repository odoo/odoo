import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("discuss.channel_commands").add("history", {
    condition: ({ store, channel }) =>
        store.has_access_livechat && channel?.channel_type === "livechat",
    help: _t("See 15 last visited pages"),
    methodName: "execute_command_history",
});
