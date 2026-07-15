import { config, onWillDestroy, plugin, Plugin, providePlugins, useScope } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { user } from "@web/core/user";
import { useEnv } from "@web/owl2/utils";

const debugRegistry = registry.category("debug");

const getAccessRights = async () => {
    const rightsToCheck = {
        "ir.ui.view": "write",
        "ir.access": "read",
    };
    const proms = Object.entries(rightsToCheck).map(([model, operation]) =>
        user.checkAccessRight(model, operation)
    );
    const [canEditView, canSeeAccess] = await Promise.all(proms);
    const accessRights = { canEditView, canSeeAccess };
    return accessRights;
};

class DebugContextPlugin extends Plugin {
    categories = config("categories") ?? new Map();
    scope = useScope();

    activateCategory(category, context) {
        const contexts = this.categories.get(category) || new Set();
        contexts.add(context);
        this.categories.set(category, contexts);

        return () => {
            contexts.delete(context);
            if (contexts.size === 0) {
                this.categories.delete(category);
            }
        };
    }

    async getItems(env) {
        const accessRights = await getAccessRights();
        return [...this.categories.entries()]
            .flatMap(([category, contexts]) =>
                debugRegistry
                    .category(category)
                    .getAll()
                    .map((factory) =>
                        this.scope.run(() =>
                            factory(Object.assign({ env, accessRights }, ...contexts))
                        )
                    )
            )
            .filter(Boolean)
            .sort((x, y) => {
                const xSeq = x.sequence || 1000;
                const ySeq = y.sequence || 1000;
                return xSeq - ySeq;
            });
    }
}
services.add(DebugContextPlugin);

export function useOwnDebugContext({ categories = [] } = {}) {
    providePlugins([DebugContextPlugin], {
        categories: new Map(categories.map((cat) => [cat, [{}]])),
    });
}

export function useEnvDebugContext() {
    return plugin(DebugContextPlugin);
}

export function useDebugCategory(category, context = {}) {
    const env = useEnv();
    if (env.debug) {
        const debugContext = useEnvDebugContext();
        onWillDestroy(debugContext.activateCategory(category, context));
    }
}
