import { user } from "@web/core/user";
import { registry } from "../registry";

import { useEffect, useEnv, useSubEnv } from "@odoo/owl";
const debugRegistry = registry.category("debug");

const getAccessRights = async () => {
    const rightsToCheck = {
        "ir.ui.view": "write",
        "ir.rule": "read",
        "ir.model.access": "read",
    };
    const proms = Object.entries(rightsToCheck).map(([model, operation]) => {
        return user.checkAccessRight(model, operation);
    });
    const [canEditView, canSeeRecordRules, canSeeModelAccess] = await Promise.all(proms);
    const accessRights = { canEditView, canSeeRecordRules, canSeeModelAccess };
    return accessRights;
};

class DebugContext {
    constructor(defaultCategories) {
        this.categories = new Map(defaultCategories.map((cat) => [cat, [{}]]));
    }

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
            .flatMap(([category, contexts]) => {
                return debugRegistry
                    .category(category)
                    .getAll()
                    .map((factory) => factory(Object.assign({ env, accessRights }, ...contexts)));
            })
            .filter(Boolean)
            .sort((x, y) => {
                const xSeq = x.sequence || 1000;
                const ySeq = y.sequence || 1000;
                return xSeq - ySeq;
            });
    }
}

const debugContextSymbol = Symbol("debugContext");
export function createDebugContext({ categories = [] } = {}) {
    return { [debugContextSymbol]: new DebugContext(categories) };
}

export function useOwnDebugContext({ categories = [] } = {}) {
    useSubEnv(createDebugContext({ categories }));
}

export function useEnvDebugContext() {
    const debugContext = useEnv()[debugContextSymbol];
    if (!debugContext) {
        throw new Error("There is no debug context available in the current environment.");
    }
    return debugContext;
}

export function useDebugCategory(category, context = {}) {
    const env = useEnv();
    if (env.debug) {
        const debugContext = useEnvDebugContext();
        useEffect(
            () => debugContext.activateCategory(category, context),
            () => []
        );
    }
}
