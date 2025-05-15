import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandProviderRegistry = registry.category("command_provider");

commandProviderRegistry.add("activity", {
    provide: (env, options) => [
        {
            name: _t("Show My Activities"),
            category: "activity",
            action() {
                env.services.action.doAction("mail.mail_activity_action_my", {
                    target: "current",
                    clearBreadcrumbs: true,
                });
            },
        },
        {
            name: _t("Show All Activities"),
            category: "activity",
            action() {
                env.services.action.doAction("mail.mail_activity_action", {
                    target: "current",
                    clearBreadcrumbs: true,
                });
            },
        },
    ],
});
