import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export const embeddedSettingsService = {
    dependencies: ["orm"],
    start(env, { orm }) {
        const embeddedActionsConfig = structuredClone(
            user.settings.embedded_actions_config_ids || {}
        );
        return {
            async fetchEmbeddedActionsConfig(embeddedActionsKey, parentActionId, currentActiveId) {
                if (!(embeddedActionsKey in embeddedActionsConfig)) {
                    const embeddedSetting = await orm.call(
                        "res.users.settings",
                        "get_embedded_actions_setting",
                        [user.settings.id, parentActionId, currentActiveId]
                    );
                    if (embeddedSetting && Object.keys(embeddedSetting).length > 0) {
                        embeddedActionsConfig[embeddedActionsKey] =
                            embeddedSetting[embeddedActionsKey];
                    }
                }
                return embeddedActionsConfig;
            },
            get embeddedActionsConfig() {
                return embeddedActionsConfig;
            },
            getEmbeddedActionsConfigKey(embeddedActionsKey, key) {
                return embeddedActionsConfig?.[embeddedActionsKey]?.[key];
            },
            setEmbeddedActionsConfig(embeddedActionsKey, parentActionId, currentActiveId, config) {
                if (embeddedActionsKey in embeddedActionsConfig) {
                    for (const [key, value] of Object.entries(config)) {
                        embeddedActionsConfig[embeddedActionsKey][key] = value;
                    }
                } else {
                    embeddedActionsConfig[embeddedActionsKey] = config;
                }
                orm.call("res.users.settings", "set_embedded_actions_setting", [
                    user.settings.id,
                    parentActionId,
                    currentActiveId,
                    config,
                ]);
            },
            hasEmbeddedActionsConfig(embeddedActionsKey) {
                return embeddedActionsKey in embeddedActionsConfig;
            },
        };
    },
};

registry.category("services").add("embedded_settings_service", embeddedSettingsService);
