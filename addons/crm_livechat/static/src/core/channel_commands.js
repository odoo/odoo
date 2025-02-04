import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("discuss.channel_commands").add("lead", {
    condition: ({ store, thread }) => store.self.type === "partner" && store.self.isInternalUser,
    help: _t("Create a new lead (/lead lead title)"),
    methodName: "execute_command_lead",
});
