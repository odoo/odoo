/** @odoo-module **/

import { clamp } from "@web/core/utils/numbers";
import { debounce, setRecurringAnimationFrame } from "@web/core/utils/timing";

/**
 * @typedef Position
 * @property {number} x
 * @property {number} y
 */

/**
 * @typedef EdgeScrollingOptions
 * @property {boolean} [enabled=true]
 * @property {number} [speed=10]
 * @property {number} [threshold=20]
 */

/**
 * @typedef DraggableBuilderParams
 *
 * Hook params
 * @property {string} [name="useAnonymousDraggable"]
 * @property {EdgeScrollingOptions} [edgeScrolling]
 * @property {Record<string, string[]>} [acceptedParams]
 * @property {Record<string, any>} [defaultParams]
 *
 * Build handlers
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
 * @property {HTMLElement | null} [currentContainer=null]
 * @property {HTMLElement | null} [currentElement=null]
 * @property {DOMRect | null} [currentElementRect=null]
 * @property {HTMLElement | null} [scrollParent=null]
 * @property {boolean} [enabled=false]
 * @property {Position} [mouse={ x: 0, y: 0 }]
 * @property {Position} [offset={ x: 0, y: 0 }]
 * @property {EdgeScrollingOptions} [edgeScrolling]
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
    edgeScrolling: ["object", "function"],
};
const DEFAULT_DEFAULT_PARAMS = {
    enable: true,
    edgeScrolling: {
        speed: 10,
        threshold: 30,
    },
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
 * Returns the bounding rect of the given element. If the `adjust` option is set
 * to true, the rect will be reduced by the padding of the element.
 * @param {HTMLElement} el
 * @param {Object} [options={}]
 * @param {boolean} [options.adjust=false]
 * @returns {DOMRect}
 */
function getRect(el, options = {}) {
    const rect = el.getBoundingClientRect();
    if (options.adjust) {
        const style = getComputedStyle(el);
        const [pl, pr, pt, pb] = [
            "padding-left",
            "padding-right",
            "padding-top",
            "padding-bottom",
        ].map((prop) => pixelValueToNumber(style.getPropertyValue(prop)));

        rect.x += pl;
        rect.y += pt;
        rect.width -= pl + pr;
        rect.height -= pt + pb;
    }
    return rect;
}

/**
 * Returns the first scrollable parent of the given element (recursively), or null
 * if none is found. A 'scrollable' element is defined by 2 things:
 *
 * - for either in width or in height: the 'scroll' value is larger than the 'client'
 * value;
 *
 * - its computed 'overflow' property is set to either "auto" or "scroll"
 *
 * If both of these assertions are true, it means that the element can effectively
 * be scrolled on at least one axis.
 * @param {HTMLElement} el
 * @returns {HTMLElement | null}
 */
function getScrollParent(el) {
    if (!el) {
        return null;
    }
    if (el.scrollWidth > el.clientWidth || el.scrollHeight > el.clientHeight) {
        const overflow = getComputedStyle(el).getPropertyValue("overflow");
        if (/\bauto\b|\bscroll\b/.test(overflow)) {
            return el;
        }
    }
    return getScrollParent(el.parentElement);
}

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 * @param {string} val
 * @returns {number}
 */
function pixelValueToNumber(val) {
    return Number(val.endsWith("px") ? val.slice(0, -2) : val);
}

/**
 * @param {DraggableBuilderParams} hookParams
 * @returns {(params: Record<any, any>) => { dragging: boolean }}
 */
export function makeDraggableHook(hookParams = {}) {
    const hookName = hookParams.name || "useAnonymousDraggable";
    const allAcceptedParams = { ...DEFAULT_ACCEPTED_PARAMS, ...hookParams.acceptedParams };
    const defaultParams = { ...DEFAULT_DEFAULT_PARAMS, ...hookParams.defaultParams };

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

                // Compute scrollable parent
                ctx.scrollParent = getScrollParent(ctx.currentContainer);

                const [eRect] = updateRects();

                // Binds handlers on eligible elements
                for (const siblingEl of ctx.ref.el.querySelectorAll(ctx.elementSelector)) {
                    if (siblingEl !== ctx.currentElement) {
                        addStyle(siblingEl, { "pointer-events": "auto" });
                    }
                }

                // Adjusts the offset
                ctx.offset.x -= eRect.x;
                ctx.offset.y -= eRect.y;

                addStyle(ctx.currentElement, {
                    position: "fixed",
                    "pointer-events": "none",
                    "z-index": 1000,
                    width: `${eRect.width}px`,
                    height: `${eRect.height}px`,
                    left: `${eRect.x}px`,
                    top: `${eRect.y}px`,
                });

                const bodyStyle = {
                    "pointer-events": "none",
                    "user-select": "none",
                };
                if (ctx.cursor) {
                    bodyStyle.cursor = ctx.cursor;
                }

                addStyle(document.body, bodyStyle);

                if (ctx.scrollParent && ctx.edgeScrolling.enabled) {
                    const cleanupFn = setRecurringAnimationFrame(handleEdgeScrolling);
                    cleanups.push(cleanupFn);
                }

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

                ctx.currentContainer = null;
                ctx.currentElement = null;
                ctx.currentElementRect = null;
                ctx.scrollParent = null;

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
             * Applies scroll to the container if the current element is near
             * the edge of the container.
             */
            const handleEdgeScrolling = (deltaTime) => {
                const [eRect, cRect] = updateRects();

                const { speed, threshold } = ctx.edgeScrolling;
                const correctedSpeed = (speed / 16) * deltaTime;
                const maxWidth = cRect.x + cRect.width;
                const maxHeight = cRect.y + cRect.height;

                const diff = {};

                if (eRect.x - cRect.x < threshold) {
                    diff.x = [eRect.x - cRect.x, -1];
                } else if (maxWidth - eRect.x - eRect.width < threshold) {
                    diff.x = [maxWidth - eRect.x - eRect.width, 1];
                }
                if (eRect.y - cRect.y < threshold) {
                    diff.y = [eRect.y - cRect.y, -1];
                } else if (maxHeight - eRect.y - eRect.height < threshold) {
                    diff.y = [maxHeight - eRect.y - eRect.height, 1];
                }

                if (diff.x || diff.y) {
                    const diffToScroll = ([delta, sign]) =>
                        (1 - clamp(delta, 0, threshold) / threshold) * correctedSpeed * sign;
                    const scrollParams = {};
                    if (diff.x) {
                        scrollParams.left = diffToScroll(diff.x);
                    }
                    if (diff.y) {
                        scrollParams.top = diffToScroll(diff.y);
                    }
                    ctx.scrollParent.scrollBy(scrollParams);
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

                ctx.currentContainer = ctx.ref.el;
                ctx.currentElement = ev.target.closest(ctx.elementSelector);

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
                    const [eRect, cRect] = updateRects();

                    // Updates the position of the dragged element.
                    ctx.currentElement.style.left = `${clamp(
                        ctx.mouse.x - ctx.offset.x,
                        cRect.x,
                        cRect.x + cRect.width - eRect.width
                    )}px`;
                    ctx.currentElement.style.top = `${clamp(
                        ctx.mouse.y - ctx.offset.y,
                        cRect.y,
                        cRect.y + cRect.height - eRect.height
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

            /**
             * @returns {DOMRect[]}
             */
            const updateRects = () => {
                // Container rect
                const containerRect = getRect(ctx.currentContainer, { adjust: true });
                if (ctx.scrollParent) {
                    // Adjust container rect according to scrollparent
                    const parentRect = getRect(ctx.scrollParent, { adjust: true });
                    containerRect.x = Math.max(containerRect.x, parentRect.x);
                    containerRect.y = Math.max(containerRect.y, parentRect.y);
                    containerRect.width = Math.min(containerRect.width, parentRect.width);
                    containerRect.height = Math.min(containerRect.height, parentRect.height);
                }

                // Element rect
                ctx.currentElementRect = getRect(ctx.currentElement);

                return [ctx.currentElementRect, containerRect];
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
                currentContainer: null,
                currentElement: null,
                currentElementRect: null,
                scrollParent: null,
                enabled: false,
                mouse: { x: 0, y: 0 },
                offset: { x: 0, y: 0 },
                edgeScrolling: { enabled: true },
            };

            // Effect depending on the params to update them.
            useEffect(
                (...deps) => {
                    const actualParams = { ...defaultParams, ...Object.fromEntries(deps) };
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

                    Object.assign(ctx.edgeScrolling, actualParams.edgeScrolling);

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
            const debouncedOnMouseMove = debounce(onMousemove, "animationFrame", true);
            useExternalListener(window, "mousemove", debouncedOnMouseMove);
            useExternalListener(window, "mouseup", onMouseup);
            useExternalListener(window, "keydown", onKeydown, true);
            onWillUnmount(() => dragEnd(true));

            return state;
        },
    }[hookName];
}
