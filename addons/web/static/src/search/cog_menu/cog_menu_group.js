// @ts-check
/** @odoo-module native */

export const COG_GROUP = Object.freeze({
    DATA: 10,
    RECORD: 20,
    APP: 40,
    PRINT: 50,
    ACTIONS: 100,
    INTEGRATE: 200,
    DANGER: 900,
});

/** @type {Set<number>} */
const COG_GROUP_NUMBERS = new Set(Object.values(COG_GROUP));

/** @param {unknown} groupNumber */
export function isCogGroup(groupNumber) {
    return typeof groupNumber === "number" && COG_GROUP_NUMBERS.has(groupNumber);
}

export const COG_MENU_REGISTRY_VALIDATION = {
    Component: Function,
    groupNumber: { type: Number, validate: isCogGroup },
    isDisplayed: { type: Function, optional: true },
    "*": true,
};

/**
 * @param {import("@web/env").OdooEnv} env
 * @param {string[]} [viewTypes]
 * @returns {boolean}
 */
export function isActWindowView(env, viewTypes) {
    const { config } = /** @type {any} */ (env);
    return (
        config?.actionType === "ir.actions.act_window" &&
        (!viewTypes || viewTypes.includes(config.viewType))
    );
}
