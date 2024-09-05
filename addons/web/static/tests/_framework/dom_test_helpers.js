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
    const focusCurrent = async () => {
        const node = await nodePromise;
        if (node !== getActiveElement(node)) {
            await pointerDown(node);
        }
        return node;
    };

    const nodePromise = waitFor(target, { visible: true, ...options });
    return {
        /**
         * @param {PointerOptions} [options]
         */
        check: (options) => check(nodePromise, options),
        /**
         * @param {FillOptions} [options]
         */
        clear: async (options) => {
            await focusCurrent();
            await clear({ confirm: "auto", ...options });
        },
        /**
         * @param {PointerOptions & KeyModifierOptions} [options]
         */
        click: async (options) => {
            const actions = [() => click(nodePromise, { ...options, delay: 0 })];
            if (options?.altKey) {
                actions.unshift(() => keyDown("Alt"));
                actions.push(() => keyUp("Alt", { delay: 0 }));
            }
            if (options?.ctrlKey) {
                actions.unshift(() => keyDown("Control"));
                actions.push(() => keyUp("Control", { delay: 0 }));
            }
            if (options?.metaKey) {
                actions.unshift(() => keyDown("Meta"));
                actions.push(() => keyUp("Meta", { delay: 0 }));
            }
            if (options?.shiftKey) {
                actions.unshift(() => keyDown("Shift"));
                actions.push(() => keyUp("Shift", { delay: 0 }));
            }

            for (const action of actions) {
                await action();
            }
            await animationFrame();
        },
        /**
         * @param {PointerOptions} [options]
         * @returns {Promise<DragHelpers>}
         */
        drag: async (options) => {
            const { moveTo } = await drag(nodePromise, { delay: advanceFrame, ...options });
            await advanceTime(500); // Wait past the mobile long touch delay
            return moveTo(nodePromise, DRAG_TOLERANCE_PARAMS);
        },
        /**
         * @param {Target} target
         * @param {PointerOptions} [dropOptions]
         * @param {PointerOptions} [dragOptions]
         */
        dragAndDrop: async (target, dropOptions, dragOptions) => {
            const to = await waitFor(target);
            const { drop, moveTo } = await drag(nodePromise, {
                delay: advanceFrame,
                ...dragOptions,
            });
            await advanceTime(500); // Wait past the mobile long touch delay
            await moveTo(nodePromise, DRAG_TOLERANCE_PARAMS);
            await drop(to, dropOptions);
        },
        /**
         * @param {InputValue} value
         * @param {FillOptions} [options]
         */
        edit: async (value, options) => {
            await focusCurrent();
            await edit(value, { confirm: "auto", ...options });
        },
        /**
         * @param {InputValue} value
         * @param {FillOptions} [options]
         */
        fill: async (value, options) => {
            await focusCurrent();
            await fill(value, { confirm: "auto", ...options });
        },
        focus: focusCurrent,
        hover: () => hover(nodePromise),
        /**
         * @param {KeyStrokes} keyStrokes
         * @param {KeyboardEventInit} [options]
         */
        press: async (keyStrokes, options) => {
            await focusCurrent();
            await press(keyStrokes, options);
        },
        /**
         * @param {Position} position
         */
        scroll: (position) => scroll(nodePromise, position),
        /**
         * @param {InputValue} value
         */
        select: (value) => select(value, { target: nodePromise }),
        /**
         * @param {PointerOptions} [options]
         */
        uncheck: (options) => uncheck(nodePromise, options),
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
    await manuallyDispatchProgrammaticEvent(queryOne(".ace_editor .ace_content"), "mousedown");

    await contains(".ace_editor textarea", { displayed: true, visible: false }).edit(value, {
        instantly: true,
    });
}
