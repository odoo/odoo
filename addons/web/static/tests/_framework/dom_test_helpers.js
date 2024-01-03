/** @odoo-module */

import {
    check,
    click,
    drag,
    edit,
    hover,
    keyDown,
    keyUp,
    pointerDown,
    press,
    queryOne,
    uncheck,
    waitFor,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { ensureArray } from "@web/core/utils/arrays";

/**
 * @typedef {import("@odoo/hoot-dom").FillOptions} FillOptions
 * @typedef {import("@odoo/hoot-dom").InputValue} InputValue
 * @typedef {import("@odoo/hoot-dom").KeyStrokes} KeyStrokes
 * @typedef {import("@odoo/hoot-dom").PointerOptions} PointerOptions
 * @typedef {import("@odoo/hoot-dom").Target} Target
 *
 * @typedef {{
 *  altKey?: boolean;
 *  ctrlKey?: boolean;
 *  metaKey?: boolean;
 *  shiftKey?: boolean;
 * }} KeyModifierOptions
 */

/**
 * @template T
 * @typedef {import("@odoo/hoot-dom").MaybePromise<T>} MaybePromise
 */

/**
 * @template T
 * @typedef {(...args: Parameters<T>) => MaybePromise<ReturnType<T>>} Promisify
 */

/**
 * @template Async
 * @typedef {import("@odoo/hoot-dom").QueryOptions} QueryOptions
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @template P, R
 * @param {(...args: P) => R} fn
 * @param  {P} args
 * @returns {() => T}
 */
const bind =
    (fn, ...args) =>
    (...additionalArgs) =>
        fn(...args, ...additionalArgs);

/**
 * @template T
 * @param {Target} target
 * @param  {...(target: Target, options: any) => MaybePromise<T>} interactions
 */
const interact = async (target, ...interactions) => {
    const actions = [];
    const options = {};
    for (const interaction of interactions) {
        if (typeof interaction === "function") {
            actions.push(interaction);
        } else {
            Object.assign(options, interaction);
        }
    }
    const targetElement = target && queryOne(target, options);
    const results = [];
    for (const interaction of actions) {
        const result = await interaction(targetElement, options);
        if (result) {
            results.push(...ensureArray(result));
        }
    }
    await animationFrame();
    return results;
};

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {Target} target
 * @param {QueryOptions} [options]
 */
export function contains(target, options) {
    if (target?.raw) {
        return contains(String.raw(...arguments));
    }
    /**
     * @template T
     * @param  {...T} actions
     */
    const run = (...actions) =>
        waitFor(target, { visible: true, ...options }).then((node) => interact(node, ...actions));
    return {
        /**
         * @param {PointerOptions} [options]
         */
        check: (options) => run(check, options),
        /**
         * @param {PointerOptions & KeyModifierOptions} [options]
         */
        click: (options) => {
            const actions = [click];
            if (options?.altKey) {
                actions.unshift(bind(keyDown, "Alt"));
                actions.push(bind(keyUp, "Alt"));
            }
            if (options?.ctrlKey) {
                actions.unshift(bind(keyDown, "Control"));
                actions.push(bind(keyUp, "Control"));
            }
            if (options?.metaKey) {
                actions.unshift(bind(keyDown, "Meta"));
                actions.push(bind(keyUp, "Meta"));
            }
            if (options?.shiftKey) {
                actions.unshift(bind(keyDown, "Shift"));
                actions.push(bind(keyUp, "Shift"));
            }
            return run(options, ...actions);
        },
        /**
         * @param {PointerOptions} [options]
         */
        drag: (options) => run(options, drag),
        /**
         * @param {InputValue} value
         * @param {FillOptions} [options]
         */
        edit: (value, options) =>
            run(pointerDown, bind(edit, value, { confirm: true, ...options })),
        focus: () => run(pointerDown),
        hover: () => run(hover),
        /**
         * @param {KeyStrokes} keyStrokes
         */
        press: (keyStrokes) => run(pointerDown, bind(press, keyStrokes)),
        /**
         * @param {PointerOptions} [options]
         */
        uncheck: (options) => run(uncheck, options),
    };
}
