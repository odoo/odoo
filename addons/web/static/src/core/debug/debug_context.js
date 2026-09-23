// @ts-check
/** @odoo-module native */

import { useEffect, useEnv, useSubEnv } from "@odoo/owl";
import { Registry, registry } from "@web/core/registry";
import { user } from "@web/core/user";
const debugRegistry = registry.category("debug");

debugRegistry.addValidation((entry) => entry instanceof Registry);

/**
 * @typedef {Object} AccessRights
 * @property {boolean} canEditView
 * @property {boolean} canSeeAccesses
 */

/** @returns {Promise<AccessRights>} */
const getAccessRights = async () => {
    const rightsToCheck = {
        "ir.ui.view": "write",
        "ir.access": "read",
    };
    const proms = Object.entries(rightsToCheck).map(([model, operation]) =>
        user.checkAccessRight(model, operation),
    );
    const [canEditView, canSeeAccesses] = await Promise.all(proms);
    return { canEditView, canSeeAccesses };
};

class DebugContext {
    /** @param {string[]} defaultCategories */
    constructor(defaultCategories) {
        /** @type {Map<string, any>} */
        this.categories = new Map(defaultCategories.map((cat) => [cat, new Set([{}])]));
    }

    /**
     * @param {string} category
     * @param {Object} context
     * @returns {() => void}
     */
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

    /**
     * @param {import("@web/env").OdooEnv} env
     * @returns {Promise<Array<import("@web/webclient/debug/debug_menu_items").DebugMenuItemDescriptor>>}
     */
    async getItems(env) {
        const accessRights = await getAccessRights();
        return /** @type {any} */ (
            [...this.categories.entries()]
                .flatMap(([category, contexts]) =>
                    debugRegistry
                        .category(category)
                        .getAll()
                        .map((factory) =>
                            factory({
                                env,
                                accessRights,
                                ...[...contexts].at(-1),
                            }),
                        ),
                )
                .filter((item) => item !== false && item != null)
                .sort((x, y) => {
                    const xSeq = (x && x.sequence) || 1000;
                    const ySeq = (y && y.sequence) || 1000;
                    return xSeq - ySeq;
                })
        );
    }
}

const debugContextSymbol = Symbol("debugContext");
/**
 * @param {{ categories?: string[] }} [options]
 * @returns {Object}
 */
export function createDebugContext({ categories = [] } = {}) {
    return /** @type {any} */ ({
        [debugContextSymbol]: new DebugContext(categories),
    });
}

/** @param {{ categories?: string[] }} [options] */
export function useOwnDebugContext({ categories = [] } = {}) {
    useSubEnv(createDebugContext({ categories }));
}

/**
 * @returns {DebugContext}
 * @throws {Error}
 */
export function useEnvDebugContext() {
    const debugContext = /** @type {any} */ (useEnv())[debugContextSymbol];
    if (!debugContext) {
        throw new Error(
            "There is no debug context available in the current environment.",
        );
    }
    return debugContext;
}

/**
 * @param {string} category
 * @param {Object} [context={}]
 */
export function useDebugCategory(category, context = {}) {
    const env = useEnv();
    if (env.debug) {
        const debugContext = useEnvDebugContext();
        useEffect(
            () => debugContext.activateCategory(category, context),
            () => [],
        );
    }
}
