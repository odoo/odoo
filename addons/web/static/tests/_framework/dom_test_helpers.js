import {
    check,
    clear,
    click,
    drag,
    edit,
    fill,
    getActiveElement,
    hover,
    keyDown,
    keyUp,
    manuallyDispatchProgrammaticEvent,
    pointerDown,
    press,
    queryOne,
    scroll,
    select,
    uncheck,
    waitFor,
} from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { getTag } from "@web/core/utils/xml";

/**
 * @typedef {import("@odoo/hoot-dom").DragHelpers} DragHelpers
 * @typedef {import("@odoo/hoot-dom").FillOptions} FillOptions
 * @typedef {import("@odoo/hoot-dom").InputValue} InputValue
 * @typedef {import("@odoo/hoot-dom").KeyStrokes} KeyStrokes
 * @typedef {import("@odoo/hoot-dom").PointerOptions} PointerOptions
 * @typedef {import("@odoo/hoot-dom").Position} Position
 * @typedef {import("@odoo/hoot-dom").QueryOptions} QueryOptions
 * @typedef {import("@odoo/hoot-dom").Target} Target
 *
 * @typedef {{
 *  altKey?: boolean;
 *  ctrlKey?: boolean;
 *  metaKey?: boolean;
 *  shiftKey?: boolean;
 * }} KeyModifierOptions
 *
 * @typedef {{
 *  cancel: () => Promise<void>;
 *  drop: () => Promise<AsyncDragHelpers>;
 *  moveTo: (...args: Parameters<DragHelpers["moveTo"]>) => Promise<void>;
 * }} AsyncDragHelpers
 */

/**
 * @template T
 * @typedef {import("@odoo/hoot-dom").MaybePromise<T>} MaybePromise
 */

/**
 * @template T
 * @typedef {(...args: Parameters<T>) => MaybePromise<ReturnType<T>>} Promisify
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

const dragEffectDelay = async () => {
    await advanceTime(20);
    await animationFrame();
};

/**
 * @param {Node} node
 */
const getConfirmAction = (node) => (getTag(node, true) === "input" ? "enter" : "blur");

/**
 * These params are used to move the pointer from an arbitrary distance in the
 * element to trigger a drag sequence (the distance required to trigger a drag
 * is defined by the `tolerance` option in the draggable hook builder).
 * @see {draggable_hook_builder.js}
 */
const DRAG_TOLERANCE_PARAMS = {
    position: {
        x: 100,
        y: 100,
    },
    relative: true,
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

    const focusCurrent = async () => {
        const node = await nodePromise;
        if (node !== getActiveElement()) {
            pointerDown(node);
        }
        return node;
    };

    const nodePromise = waitFor(target, { visible: true, ...options });
    return {
        /**
         * @param {PointerOptions} [options]
         */
        check: async (options) => {
            check(await nodePromise, options);
            await animationFrame();
        },
        /**
         * @param {FillOptions} [options]
         */
        clear: async (options) => {
            const node = await focusCurrent();
            clear({ confirm: getConfirmAction(node), ...options });
            await animationFrame();
        },
        /**
         * @param {PointerOptions & KeyModifierOptions} [options]
         */
        click: async (options) => {
            const actions = [() => click(node, options)];
            if (options?.altKey) {
                actions.unshift(() => keyDown("Alt"));
                actions.push(() => keyUp("Alt"));
            }
            if (options?.ctrlKey) {
                actions.unshift(() => keyDown("Control"));
                actions.push(() => keyUp("Control"));
            }
            if (options?.metaKey) {
                actions.unshift(() => keyDown("Meta"));
                actions.push(() => keyUp("Meta"));
            }
            if (options?.shiftKey) {
                actions.unshift(() => keyDown("Shift"));
                actions.push(() => keyUp("Shift"));
            }

            const node = await nodePromise;
            for (const action of actions) {
                action();
            }
            await animationFrame();
        },
        /**
         * @param {PointerOptions} [options]
         * @returns {Promise<AsyncDragHelpers>}
         */
        drag: async (options) => {
            /** @type {AsyncDragHelpers["cancel"]} */
            const asyncCancel = async () => {
                cancel();
                await dragEffectDelay();
            };

            /** @type {AsyncDragHelpers["drop"]} */
            const asyncDrop = async () => {
                drop();
                await dragEffectDelay();
            };

            /** @type {AsyncDragHelpers["moveTo"]} */
            const asyncMoveTo = async (to, options) => {
                moveTo(to, options);
                await dragEffectDelay();
            };

            const node = await nodePromise;
            const { cancel, drop, moveTo } = drag(node, options);
            await dragEffectDelay();

            hover(node, DRAG_TOLERANCE_PARAMS);
            await dragEffectDelay();

            return {
                cancel: asyncCancel,
                drop: asyncDrop,
                moveTo: asyncMoveTo,
            };
        },
        /**
         * @param {Target} target
         * @param {PointerOptions} [options]
         */
        dragAndDrop: async (target, options) => {
            const [from, to] = await Promise.all([nodePromise, waitFor(target)]);
            const { drop, moveTo } = drag(from);
            await dragEffectDelay();

            hover(from, DRAG_TOLERANCE_PARAMS);
            await dragEffectDelay();

            moveTo(to, options);
            await dragEffectDelay();

            drop();
            await dragEffectDelay();
        },
        /**
         * @param {InputValue} value
         * @param {FillOptions} [options]
         */
        edit: async (value, options) => {
            const node = await focusCurrent();
            edit(value, { confirm: getConfirmAction(node), ...options });
            await animationFrame();
        },
        /**
         * @param {InputValue} value
         * @param {FillOptions} [options]
         */
        fill: async (value, options) => {
            const node = await focusCurrent();
            fill(value, { confirm: getConfirmAction(node), ...options });
            await animationFrame();
        },
        focus: async () => {
            await focusCurrent();
            await animationFrame();
        },
        hover: async () => {
            hover(await nodePromise);
            await animationFrame();
        },
        /**
         * @param {KeyStrokes} keyStrokes
         * @param {KeyboardEventInit} [options]
         */
        press: async (keyStrokes, options) => {
            await focusCurrent();
            press(keyStrokes, options);
            await animationFrame();
        },
        /**
         * @param {Position} position
         */
        scroll: async (position) => {
            scroll(await nodePromise, position);
            await animationFrame();
        },
        /**
         * @param {InputValue} value
         */
        select: async (value) => {
            select(value, { target: await nodePromise });
            await animationFrame();
        },
        /**
         * @param {PointerOptions} [options]
         */
        uncheck: async (options) => {
            uncheck(await nodePromise, options);
            await animationFrame();
        },
    };
}

/**
 * @param {string} value
 */
export async function editAce(value) {
    // Ace editor traps focus on "mousedown" events, which are not triggered in
    // mobile. To support both environments, a single "mouedown" event is triggered
    // in this specific case. This should not be reproduced and is only accepted
    // because the tested behaviour comes from a lib on which we have no control.
    manuallyDispatchProgrammaticEvent(queryOne(".ace_editor .ace_content"), "mousedown");

    await contains(".ace_editor textarea", { displayed: true, visible: false }).edit(value, {
        instantly: true,
    });
}
