import {
    advanceFrame,
    advanceTime,
    after,
    afterEach,
    animationFrame,
    check,
    clear,
    click,
    dblclick,
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
} from "@odoo/hoot";
import { hasTouch } from "@web/core/browser/feature_detection";

/**
 * @typedef {import("@odoo/hoot").DragHelpers} DragHelpers
 * @typedef {import("@odoo/hoot").DragOptions} DragOptions
 * @typedef {import("@odoo/hoot").FillOptions} FillOptions
 * @typedef {import("@odoo/hoot").InputValue} InputValue
 * @typedef {import("@odoo/hoot").KeyStrokes} KeyStrokes
 * @typedef {import("@odoo/hoot").PointerOptions} PointerOptions
 * @typedef {import("@odoo/hoot").Position} Position
 * @typedef {import("@odoo/hoot").QueryOptions} QueryOptions
 * @typedef {import("@odoo/hoot").Target} Target
 *
 * @typedef {DragOptions & {
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
 */

/**
 * @template T
 * @typedef {T | PromiseLike<T>} MaybePromise
 */

/**
 * @template T
 * @typedef {(...args: Parameters<T>) => MaybePromise<ReturnType<T>>} Promisify
 */

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {typeof click} clickFn
 * @param {Promise<Element>} nodePromise
 * @param {PointerOptions & KeyModifierOptions} [options]
 */
const callClick = async (clickFn, nodePromise, options) => {
    const actions = [() => clickFn(nodePromise, options)];
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

    for (const action of actions) {
        await action();
    }
    await animationFrame();
};

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
    await hover(node, { position, relative: true });
    await advanceFrame();
};

/**
 * @param {number} [delay]
 * These params are used to move the pointer from an arbitrary distance in the
 * element to trigger a drag sequence (the distance required to trigger a drag
 * is defined by the `tolerance` option in the draggable hook builder).
 * @see {draggable_hook_builder.js}
 */
const waitForTouchDelay = async (delay) => {
    if (hasTouch()) {
        await advanceTime(delay || 500);
    }
};

/** @type {(() => any) | null} */
let cancelCurrentDragSequence = null;
/** @type {Target[]} */
const unconsumedContains = [];

afterEach(async () => {
    if (cancelCurrentDragSequence) {
        await cancelCurrentDragSequence();
    }
    if (unconsumedContains.length) {
        const targets = unconsumedContains.map(String).join(", ");
        unconsumedContains.length = 0;
        throw new Error(
            `called 'contains' on "${targets}" without any action: use 'waitFor' if no interaction is intended`
        );
    }
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * @param {Target} target
 * @param {QueryOptions} [options]
 */
export function contains(target, options) {
    const consumeContains = () => {
        if (!consumed) {
            consumed = true;
            unconsumedContains.pop();
        }
    };

    const focusCurrent = async () => {
        const node = await nodePromise;
        if (node !== getActiveElement(node)) {
            await pointerDown(node);
        }
        return node;
    };

    let consumed = false;
    unconsumedContains.push(target);

    /** @type {Promise<Element>} */
    const nodePromise = waitFor.as("contains")(target, { visible: true, ...options });
    return {
        /**
         * @param {PointerOptions} [options]
         */
        check: async (options) => {
            consumeContains();
            await check(nodePromise, options);
            await animationFrame();
        },
        /**
         * @param {FillOptions} [options]
         */
        clear: async (options) => {
            consumeContains();
            await focusCurrent();
            await clear({ confirm: "auto", ...options });
            await animationFrame();
        },
        /**
         * @param {PointerOptions & KeyModifierOptions} [options]
         */
        click: async (options) => {
            consumeContains();
            await callClick(click, nodePromise, options);
        },
        /**
         * @param {PointerOptions & KeyModifierOptions} [options]
         */
        dblclick: async (options) => {
            consumeContains();
            await callClick(dblclick, nodePromise, options);
        },
        /**
         * @param {DragAndDropOptions} [options]
         * @returns {Promise<DragHelpers>}
         */
        drag: async (options) => {
            /** @type {typeof cancel} */
            const cancelWithDelay = async (options) => {
                await cancel(options);
                await advanceFrame();
                cancelCurrentDragSequence = null;
            };

            /** @type {typeof drop} */
            const dropWithDelay = async (to, options) => {
                if (to) {
                    await moveToWithDelay(to, options);
                }
                await drop();
                await advanceFrame();
                cancelCurrentDragSequence = null;
            };

            /** @type {typeof moveTo} */
            const moveToWithDelay = async (to, options) => {
                await moveTo(to, options);
                await advanceFrame();

                return helpersWithDelay;
            };

            consumeContains();

            await cancelCurrentDragSequence?.();
            cancelCurrentDragSequence = cancelWithDelay;

            const { cancel, drop, moveTo } = await drag(nodePromise, options);
            const helpersWithDelay = {
                cancel: cancelWithDelay,
                drop: dropWithDelay,
                moveTo: moveToWithDelay,
            };

            await waitForTouchDelay(options?.pointerDownDuration);

            await dragForTolerance(nodePromise, options?.initialPointerMoveDistance);

            return helpersWithDelay;
        },
        /**
         * @param {Target} target
         * @param {DragAndDropOptions} [dropOptions]
         * @param {DragOptions} [dragOptions]
         */
        dragAndDrop: async (target, dropOptions, dragOptions) => {
            consumeContains();

            await cancelCurrentDragSequence?.();

            const [from, to] = await Promise.all([nodePromise, waitFor(target)]);
            const { drop, moveTo } = await drag(from, dragOptions);

            await waitForTouchDelay(dropOptions?.pointerDownDuration);

            await dragForTolerance(from, dropOptions?.initialPointerMoveDistance);

            await moveTo(to, dropOptions);
            await advanceFrame();

            await drop();
            await advanceFrame();
        },
        /**
         * @param {InputValue} value
         * @param {FillOptions} [options]
         */
        edit: async (value, options) => {
            consumeContains();
            await focusCurrent();
            await edit(value, { confirm: "auto", ...options });
            await animationFrame();
        },
        /**
         * @param {InputValue} value
         * @param {FillOptions} [options]
         */
        fill: async (value, options) => {
            consumeContains();
            await focusCurrent();
            await fill(value, { confirm: "auto", ...options });
            await animationFrame();
        },
        focus: async () => {
            consumeContains();
            await focusCurrent();
            await animationFrame();
        },
        hover: async () => {
            consumeContains();
            await hover(nodePromise);
            await animationFrame();
        },
        /**
         * @param {KeyStrokes} keyStrokes
         * @param {KeyboardEventInit} [options]
         */
        keyDown: async (keyStrokes, options) => {
            consumeContains();
            await focusCurrent();
            await keyDown(keyStrokes, options);
            await animationFrame();
        },
        /**
         * @param {KeyStrokes} keyStrokes
         * @param {KeyboardEventInit} [options]
         */
        keyUp: async (keyStrokes, options) => {
            consumeContains();
            await focusCurrent();
            await keyUp(keyStrokes, options);
            await animationFrame();
        },
        /**
         * @param {KeyStrokes} keyStrokes
         * @param {KeyboardEventInit} [options]
         */
        press: async (keyStrokes, options) => {
            consumeContains();
            await focusCurrent();
            await press(keyStrokes, options);
            await animationFrame();
        },
        /**
         * @param {Position} position
         */
        scroll: async (position) => {
            consumeContains();
            // disable "scrollable" check
            await scroll(nodePromise, position, { scrollable: false, ...options });
            await animationFrame();
        },
        /**
         * @param {InputValue} value
         */
        select: async (value) => {
            consumeContains();
            await select(value, { target: nodePromise });
            await animationFrame();
        },
        /**
         * @param {InputValue} value
         */
        selectDropdownItem: async (value) => {
            consumeContains();
            await callClick(click, queryOne(".dropdown-toggle", { root: await nodePromise }));
            const item = await waitFor(`.dropdown-item:contains(${value})`);
            await callClick(click, item);
            await animationFrame();
        },
        /**
         * @param {PointerOptions} [options]
         */
        uncheck: async (options) => {
            consumeContains();
            await uncheck(nodePromise, options);
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
    await manuallyDispatchProgrammaticEvent(queryOne(".ace_editor .ace_content"), "mousedown");

    await contains(".ace_editor textarea", { displayed: true, visible: false }).edit(value, {
        instantly: true,
    });
}
