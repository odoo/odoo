// @ts-check

/** @module @web/services/debug/debug_context - Debug context manager that collects and merges debug menu items by category */

import { useEffect, useEnv, useSubEnv } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { user } from "@web/services/user";
const debugRegistry = registry.category("debug");

/**
 * @typedef {Object} AccessRights
 * @property {boolean} canEditView
 * @property {boolean} canSeeRecordRules
 * @property {boolean} canSeeModelAccess
 */

/**
 * Fetch the current user's debug-relevant access rights.
 * @returns {Promise<AccessRights>}
 */
const getAccessRights = async () => {
    const rightsToCheck = {
        "ir.ui.view": "write",
        "ir.rule": "read",
        "ir.model.access": "read",
    };
    const proms = Object.entries(rightsToCheck).map(([model, operation]) =>
        user.checkAccessRight(model, operation),
    );
    const [canEditView, canSeeRecordRules, canSeeModelAccess] =
        await Promise.all(proms);
    const accessRights = { canEditView, canSeeRecordRules, canSeeModelAccess };
    return accessRights;
};

/**
 * Manages debug menu categories and their associated context data.
 * Each category maps to a set of context objects that are merged when
 * generating debug menu items.
 */
class DebugContext {
    /** @param {string[]} defaultCategories - initial category names to register */
    constructor(defaultCategories) {
        /** @type {Map<string, any>} */
        this.categories = new Map(defaultCategories.map((cat) => [cat, [{}]]));
    }

    /**
     * Activate a debug category with context data. Returns a cleanup function.
     * @param {string} category - the category key (e.g. "default", "form")
     * @param {Object} context - contextual data passed to debug item factories
     * @returns {() => void} deactivation function
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
     * Collect all debug menu items from all active categories.
     * Calls each registered factory with the merged context and access rights.
     * @param {import("@web/env").OdooEnv} env
     * @returns {Promise<Array<import("./debug_menu_items").DebugMenuItemDescriptor>>}
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
                            factory(Object.assign({ env, accessRights }, ...contexts)),
                        ),
                )
                .filter(Boolean)
                .sort((x, y) => {
                    const xSeq = x.sequence || 1000;
                    const ySeq = y.sequence || 1000;
                    return xSeq - ySeq;
                })
        );
    }
}

const debugContextSymbol = Symbol("debugContext");
/**
 * Create a debug context object to be injected into the OWL environment.
 * @param {{ categories?: string[] }} [options]
 * @returns {Object} env extension containing the debug context under a private symbol
 */
export function createDebugContext({ categories = [] } = {}) {
    return /** @type {any} */ ({
        [debugContextSymbol]: new DebugContext(categories),
    });
}

/**
 * OWL hook: create and inject a new debug context into the component's sub-environment.
 * @param {{ categories?: string[] }} [options]
 */
export function useOwnDebugContext({ categories = [] } = {}) {
    useSubEnv(createDebugContext({ categories }));
}

/**
 * OWL hook: retrieve the debug context from the current environment.
 * @returns {DebugContext}
 * @throws {Error} if no debug context is available
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
 * OWL hook: register a debug category for the current component's lifetime.
 * The category is automatically deactivated when the component is destroyed.
 * @param {string} category - the category to activate (e.g. "form", "list")
 * @param {Object} [context={}] - contextual data for debug item factories
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
