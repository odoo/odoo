import { after } from "@odoo/hoot";
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
import { advanceFrame, advanceTime, animationFrame } from "@odoo/hoot-mock";
import { hasTouch } from "@web/core/browser/feature_detection";
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
 * @typedef {PointerOptions & {
 *  initialPointerMoveDistance?: number;
 *  pointerDownDuration: number;
 * }} DragAndDropOptions
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

/**
 * @param {Node} node
 * @param {number} [distance]
 */
const dragForTolerance = async (node, distance) => {
    if (distance === 0) {
        return;
    }

    const position = {
        x: distance || 100,
        y: distance || 100,
    };
    hover(node, { position, relative: true });
    await advanceFrame();
};

/**
 * @param {Node} node
 */
const getConfirmAction = (node) => (getTag(node, true) === "input" ? "enter" : "blur");

/**
 * @param {number} [delay]
 */
const waitForTouchDelay = async (delay) => {
    if (hasTouch()) {
        await advanceTime(delay || 500);
    }
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
         * @param {DragAndDropOptions} [options]
         * @returns {Promise<AsyncDragHelpers>}
         */
        drag: async (options) => {
            /** @type {AsyncDragHelpers["cancel"]} */
            const asyncCancel = async () => {
                cancel();
                await advanceFrame();
            };

            /** @type {AsyncDragHelpers["drop"]} */
            const asyncDrop = async () => {
                drop();
                await advanceFrame();
            };

            /** @type {AsyncDragHelpers["moveTo"]} */
            const asyncMoveTo = async (to, options) => {
                moveTo(to, options);
                await advanceFrame();
            };

            const node = await nodePromise;
            const { cancel, drop, moveTo } = drag(node, options);

            await waitForTouchDelay(options?.pointerDownDuration);

            await dragForTolerance(node, options?.initialPointerMoveDistance);

            return {
                cancel: asyncCancel,
                drop: asyncDrop,
                moveTo: asyncMoveTo,
            };
        },
        /**
         * @param {Target} target
         * @param {DragAndDropOptions} [options]
         */
        dragAndDrop: async (target, options) => {
            const [from, to] = await Promise.all([nodePromise, waitFor(target)]);
            const { drop, moveTo } = drag(from);

            await waitForTouchDelay(options?.pointerDownDuration);

            await dragForTolerance(from, options?.initialPointerMoveDistance);

            moveTo(to, options);
            await advanceFrame();

            drop();
            await advanceFrame();
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
 * @param {string} style
 */
export function defineStyle(style) {
    const styleEl = document.createElement("style");
    styleEl.textContent = style;

    document.head.appendChild(styleEl);
    after(() => styleEl.remove());
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
