import { router } from "@web/core/browser/router";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const commandProviderRegistry = registry.category("command_provider");

if (commandProviderRegistry.contains("debug")) {
    const { provide } = commandProviderRegistry.get("debug");

    commandProviderRegistry.add(
        "debug",
        {
            provide: (env, options) => {
                const result = provide(env, options);
                const existingDebugKeys = new Set(env.debug?.split(",").filter(Boolean) || []);
                if (existingDebugKeys.has("translate")) {
                    result.unshift({
                        action() {
                            existingDebugKeys.delete("translate");
                            router.pushState(
                                { debug: [...existingDebugKeys].join(",") },
                                { reload: true }
                            );
                        },
                        category: "debug",
                        name: _t("Deactivate interactive translation mode"),
                    });
                } else {
                    result.unshift({
                        action() {
                            existingDebugKeys.add("translate");
                            router.pushState(
                                { debug: [...existingDebugKeys].join(",") },
                                { reload: true }
                            );
                        },
                        category: "debug",
                        name: _t("Activate interactive translation mode"),
                    });
                }
                return result;
            },
        },
        { force: true }
    );
}
