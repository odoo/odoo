/** @odoo-module **/

import { clamp } from "@web/core/utils/numbers";
import { debounce } from "@web/core/utils/timing";

/**
 * @typedef Position
 * @property {number} x
 * @property {number} y
 */

/**
 * @typedef DraggableBuilderParams
 *
 * Hook params
 * @property {string} [name="useAnonymousDraggable"]
 * @property {Record<string, string[]>} [acceptedParams]
 *
 * Build handlers
 * @property {(params: DraggableBuilderHookParams) => any} onBuildSetup
 * @property {(params: DraggableBuilderHookParams) => any} onComputeParams
 *
 * Runtime handlers
 * @property {(params: DraggableBuilderHookParams) => any} onWillStartDrag
 * @property {(params: DraggableBuilderHookParams) => any} onDragStart
 * @property {(params: DraggableBuilderHookParams) => any} onDrag
 * @property {(params: DraggableBuilderHookParams) => any} onDragEnd
 * @property {(params: DraggableBuilderHookParams) => any} onDrop
 * @property {(params: DraggableBuilderHookParams) => any} onCleanup
 */

/**
 * @typedef DraggableHookRunningContext
 * @property {{ el: HTMLElement | null }} ref
 * @property {string | null} [elementSelector=null]
 * @property {string | null} [ignoreSelector=null]
 * @property {string | null} [fullSelector=null]
 * @property {string | null} [cursor=null]
 * @property {HTMLElement | null} [currentContainerEl=null]
 * @property {DOMRect | null} [currentContainerRect=null]
 * @property {HTMLElement | null} [currentElement=null]
 * @property {DOMRect | null} [currentElementRect=null]
 * @property {boolean} [enabled=false]
 * @property {Position} [mouse={ x: 0, y: 0 }]
 * @property {Position} [offset={ x: 0, y: 0 }]
 */

/**
 * @typedef DraggableBuilderHookParams
 * @property {DraggableHookRunningContext} ctx
 * @property {Object} helpers
 * @property {Function} helpers.addListener
 * @property {Function} helpers.addStyle
 * @property {Function} helpers.execHandler
 */

const { useEffect, useEnv, useExternalListener, onWillUnmount, reactive } = owl;

const DEFAULT_ACCEPTED_PARAMS = {
    enable: ["boolean", "function"],
    ref: ["object"],
    elements: ["string"],
    handle: ["string", "function"],
    ignore: ["string", "function"],
    cursor: ["string"],
};
const LEFT_CLICK = 0;
const MANDATORY_PARAMS = ["ref", "elements"];

/**
 * Cancels the default behavior and propagation of a given event.
 * @param {Event} ev
 */
function cancelEvent(ev) {
    ev.stopPropagation();
    ev.stopImmediatePropagation();
    ev.preventDefault();
}

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 * @param {string} val
 * @returns {number}
 */
function cssValueToNumber(val) {
    return Number(val.slice(0, -2));
}

/**
 * @param {DraggableBuilderParams} hookParams
 * @returns {(params: Record<any, any>) => { dragging: boolean }}
 */
export function makeDraggableHook(hookParams = {}) {
    const hookName = hookParams.name || "useAnonymousDraggable";
    const allAcceptedParams = { ...DEFAULT_ACCEPTED_PARAMS, ...hookParams.acceptedParams };

    /**
     * @param {SortableParams} params
     * @returns {[string, string | boolean][]}
     */
    const computeParams = (params) => {
        const computedParams = { enable: true };
        for (const prop in allAcceptedParams) {
            if (prop in params) {
                computedParams[prop] = params[prop];
                if (typeof params[prop] === "function") {
                    computedParams[prop] = computedParams[prop]();
                }
            }
        }
        return Object.entries(computedParams);
    };

    /**
     * Basic error builder for the hook.
     * @param {string} reason
     * @returns {Error}
     */
    const makeError = (reason) => new Error(`Error in hook ${hookName}: ${reason}.`);

    return {
        [hookName](params) {
            /**
             * Adds an event listener to be cleaned up after the next drag sequence
             * has stopped. An additionnal `timeout` param allows the handler to be
             * delayed after a timeout.
             * @param {EventTarget} el
             * @param {string} event
             * @param {(...args: any[]) => any} callback
             * @param {boolean | Record<string, boolean>} [options]
             */
            const addListener = (el, event, callback, options) => {
                el.addEventListener(event, callback, options);
                cleanups.push(() => el.removeEventListener(event, callback, options));
            };

            /**
             * Adds style to an element to be cleaned up after the next drag sequence has
             * stopped.
             * @param {HTMLElement} el
             * @param {Record<string, string | number>} style
             */
            const addStyle = (el, style) => {
                const originalStyle = el.getAttribute("style");
                cleanups.push(() =>
                    originalStyle
                        ? el.setAttribute("style", originalStyle)
                        : el.removeAttribute("style")
                );
                for (const key in style) {
                    el.style[key] = style[key];
                }
            };

            /**
             * Main entry function to start a drag sequence.
             */
            const dragStart = () => {
                state.dragging = true;

                // Calculates the bounding rectangles of the current element, and of the
                // container element (`parentElement` or `ref.el`).
                const containerStyle = getComputedStyle(ctx.currentContainerEl);
                const [pleft, pright, ptop, pbottom] = [
                    "padding-left",
                    "padding-right",
                    "padding-top",
                    "padding-bottom",
                ].map((prop) => cssValueToNumber(containerStyle.getPropertyValue(prop)));

                ctx.currentElementRect = ctx.currentElement.getBoundingClientRect();
                ctx.currentContainerRect = ctx.currentContainerEl.getBoundingClientRect();
                const { x, y, width, height } = ctx.currentElementRect;

                // Reduces the container's dimensions according to its padding.
                ctx.currentContainerRect.x += pleft;
                ctx.currentContainerRect.width -= pleft + pright;
                ctx.currentContainerRect.y += ptop;
                ctx.currentContainerRect.height -= ptop + pbottom;

                // Binds handlers on eligible elements
                for (const siblingEl of ctx.ref.el.querySelectorAll(ctx.elementSelector)) {
                    if (siblingEl !== ctx.currentElement) {
                        addStyle(siblingEl, { "pointer-events": "auto" });
                    }
                }

                // Adjusts the offset
                ctx.offset.x -= x;
                ctx.offset.y -= y;

                addStyle(ctx.currentElement, {
                    position: "fixed",
                    "pointer-events": "none",
                    "z-index": 1000,
                    width: `${width}px`,
                    height: `${height}px`,
                    left: `${x}px`,
                    top: `${y}px`,
                });

                const bodyStyle = {
                    "pointer-events": "none",
                    "user-select": "none",
                };
                if (ctx.cursor) {
                    bodyStyle.cursor = ctx.cursor;
                }

                addStyle(document.body, bodyStyle);

                execBuildHandler("onDragStart");
            };

            /**
             * Main exit function to stop a drag sequence. Note that it can be called
             * even if a drag sequence did not start yet to perform a cleanup of all
             * current context variables.
             * @param {boolean} cancelled
             * @param {boolean} [inErrorState] can be set to true when an error
             *  occurred to avoid falling into an infinite loop if the error
             *  originated from one of the handlers.
             */
            const dragEnd = (cancelled, inErrorState) => {
                if (state.dragging) {
                    if (!inErrorState) {
                        execBuildHandler("onDragEnd");
                        if (!cancelled) {
                            execBuildHandler("onDrop");
                        }
                    }
                }

                execBuildHandler("onCleanup");

                // Performs all registered clean-ups.
                while (cleanups.length) {
                    cleanups.pop()();
                }

                ctx.currentElement = null;
                ctx.currentElementRect = null;

                ctx.currentContainerEl = null;
                ctx.currentContainerRect = null;

                state.dragging = false;
            };

            /**
             * Executes a handler from the `hookParams`.
             * @param {string} fnName
             * @param {Record<any, any>} arg
             */
            const execBuildHandler = (fnName, arg) => {
                if (typeof hookParams[fnName] === "function") {
                    hookParams[fnName]({ ctx, helpers: buildHelpers, ...arg });
                }
            };

            /**
             * Safely executes a handler from the `params`, so that the drag sequence can
             * be interrupted if an error occurs.
             * @param {string} callbackName
             * @param {Record<any, any>} arg
             */
            const execHandler = (callbackName, arg) => {
                if (typeof params[callbackName] === "function") {
                    try {
                        params[callbackName]({ ...ctx.mouse, ...arg });
                    } catch (err) {
                        dragEnd(true, true);
                        throw err;
                    }
                }
            };

            /**
             * Window "keydown" event handler.
             * @param {KeyboardEvent} ev
             */
            const onKeydown = (ev) => {
                if (!ctx.enabled || !state.dragging) {
                    return;
                }
                switch (ev.key) {
                    case "Escape":
                    case "Tab": {
                        cancelEvent(ev);
                        dragEnd(true);
                    }
                }
            };

            /**
             * Global (= ref) "mousedown" event handler.
             * @param {MouseEvent} ev
             */
            const onMousedown = (ev) => {
                updateMousePosition(ev);

                // A drag sequence can still be in progress if the mouseup occurred
                // outside of the window.
                dragEnd(true);

                if (
                    ev.button !== LEFT_CLICK ||
                    !ctx.enabled ||
                    !ev.target.closest(ctx.fullSelector) ||
                    (ctx.ignoreSelector && ev.target.closest(ctx.ignoreSelector))
                ) {
                    return;
                }

                ctx.currentElement = ev.target.closest(ctx.elementSelector);
                ctx.currentContainerEl = ctx.ref.el;

                Object.assign(ctx.offset, ctx.mouse);

                execBuildHandler("onWillStartDrag");
            };

            /**
             * Window "mousemove" event handler.
             * @param {MouseEvent} ev
             */
            const onMousemove = (ev) => {
                updateMousePosition(ev);

                if (!ctx.enabled || !ctx.currentElement) {
                    return;
                }
                if (!state.dragging) {
                    dragStart();
                }
                if (state.dragging) {
                    // Updates the position of the dragged element.
                    ctx.currentElement.style.left = `${clamp(
                        ctx.mouse.x - ctx.offset.x,
                        ctx.currentContainerRect.x,
                        ctx.currentContainerRect.x +
                            ctx.currentContainerRect.width -
                            ctx.currentElementRect.width
                    )}px`;
                    ctx.currentElement.style.top = `${clamp(
                        ctx.mouse.y - ctx.offset.y,
                        ctx.currentContainerRect.y,
                        ctx.currentContainerRect.y +
                            ctx.currentContainerRect.height -
                            ctx.currentElementRect.height
                    )}px`;

                    execBuildHandler("onDrag");
                }
            };

            /**
             * Window "mouseup" event handler.
             * @param {MouseEvent} ev
             */
            const onMouseup = (ev) => {
                updateMousePosition(ev);
                dragEnd(false);
            };

            /**
             * Updates the current mouse position from a given event.
             * @param {MouseEvent} ev
             */
            const updateMousePosition = (ev) => {
                ctx.mouse.x = ev.clientX;
                ctx.mouse.y = ev.clientY;
            };

            // Component infos
            const env = useEnv();
            const state = reactive({ dragging: false });

            // Basic error handling asserting that the parameters are valid.
            for (const prop in allAcceptedParams) {
                if (params[prop] && !allAcceptedParams[prop].includes(typeof params[prop])) {
                    throw makeError(`invalid type for property "${prop}" in parameters`);
                } else if (!params[prop] && MANDATORY_PARAMS.includes(prop)) {
                    throw makeError(`missing required property "${prop}" in parameters`);
                }
            }

            // Build helpers
            const buildHelpers = { addListener, addStyle, execHandler };

            /** @type {(() => any)[]} */
            const cleanups = [];

            /** @type {DraggableHookRunningContext} */
            const ctx = {
                ref: params.ref,
                ignoreSelector: null,
                fullSelector: null,
                cursor: null,
                currentContainerEl: null,
                currentContainerRect: null,
                currentElement: null,
                currentElementRect: null,
                enabled: false,
                mouse: { x: 0, y: 0 },
                offset: { x: 0, y: 0 },
            };

            execBuildHandler("onBuildSetup");

            // Effect depending on the params to update them.
            useEffect(
                (...deps) => {
                    const actualParams = Object.fromEntries(deps);
                    ctx.enabled = Boolean(ctx.ref.el && !env.isSmall && actualParams.enable);
                    if (!ctx.enabled) {
                        return;
                    }

                    // Selectors
                    ctx.elementSelector = actualParams.elements;
                    if (!ctx.elementSelector) {
                        throw makeError(
                            `no value found by "elements" selector: ${ctx.elementSelector}`
                        );
                    }
                    const allSelectors = [ctx.elementSelector];
                    ctx.cursor = actualParams.cursor || null;
                    if (actualParams.handle) {
                        allSelectors.push(actualParams.handle);
                    }
                    if (actualParams.ignore) {
                        ctx.ignoreSelector = actualParams.ignore;
                    }
                    ctx.fullSelector = allSelectors.join(" ");

                    execBuildHandler("onComputeParams", { params: actualParams });
                },
                () => computeParams(params)
            );
            // Effect depending on the `ref.el` to add triggering mouse events listener.
            useEffect(
                (el) => {
                    if (el) {
                        el.addEventListener("mousedown", onMousedown);
                        return () => el.removeEventListener("mousedown", onMousedown);
                    }
                },
                () => [ctx.ref.el]
            );
            // Other global mouse event listeners.
            const debouncedMousemove = debounce(onMousemove, "animationFrame", true);
            useExternalListener(window, "mousemove", debouncedMousemove);
            useExternalListener(window, "mouseup", onMouseup);
            useExternalListener(window, "keydown", onKeydown, true);
            onWillUnmount(() => dragEnd(true));

            return state;
        },
    }[hookName];
}
