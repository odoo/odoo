/** @odoo-module **/

import { onWillUnmount, reactive, useEffect, useExternalListener } from "@odoo/owl";
import { clamp } from "@web/core/utils/numbers";
import { setRecurringAnimationFrame, useThrottleForAnimation } from "@web/core/utils/timing";

/**
 * @typedef CleanupManager
 * @property {(cleanupFn: Function) => void} add
 * @property {() => void} cleanup
 *
 * @typedef DOMHelpers
 * @property {(el: HTMLElement, ...classNames: string[]) => void} addClass
 * @property {(el: EventTarget, event: string, callback: (...args: any[]) => any, options?: boolean | Record<string, boolean>) => void} addListener
 * @property {(el: HTMLElement, style: Record<string, string | number>) => void} addStyle
 * @property {(el: HTMLElement, options?: { adjust?: boolean }) => DOMRect} getRect
 * @property {(el: HTMLElement, ...classNames: string[]) => void} removeClass
 * @property {(el: HTMLElement, properties: string[]) => void} removeStyle
 *
 * @typedef DraggableBuilderParams
 * Hook params
 * @property {string} [name="useAnonymousDraggable"]
 * @property {EdgeScrollingOptions} [edgeScrolling]
 * @property {Record<string, string[]>} [acceptedParams]
 * @property {Record<string, any>} [defaultParams]
 * Build hooks
 * @property {(params: DraggableBuildHandlerParams) => any} onComputeParams
 * Runtime hooks
 * @property {(params: DraggableBuildHandlerParams) => any} onDragStart
 * @property {(params: DraggableBuildHandlerParams) => any} onDrag
 * @property {(params: DraggableBuildHandlerParams) => any} onDragEnd
 * @property {(params: DraggableBuildHandlerParams) => any} onDrop
 * @property {(params: DraggableBuildHandlerParams) => any} onWillStartDrag
 *
 * @typedef DraggableHookContext
 * @property {{ el: HTMLElement | null }} ref
 * @property {string | null} [elementSelector=null]
 * @property {string | null} [ignoreSelector=null]
 * @property {string | null} [fullSelector=null]
 * @property {boolean} [followCursor=true]
 * @property {string | null} [cursor=null]
 * @property {() => boolean} [enable=() => false]
 * @property {Position} [mouse={ x: 0, y: 0 }]
 * @property {EdgeScrollingOptions} [edgeScrolling]
 * @property {number} [tolerance]
 * @property {DraggableHookCurrentContext} current
 *
 * @typedef DraggableHookCurrentContext
 * @property {HTMLElement} [current.container]
 * @property {DOMRect} [current.containerRect]
 * @property {HTMLElement} [current.element]
 * @property {DOMRect} [current.elementRect]
 * @property {HTMLElement} [scrollParent]
 * @property {Position} [initialPosition]
 * @property {Position} [offset={ x: 0, y: 0 }]
 *
 * @typedef EdgeScrollingOptions
 * @property {boolean} [enabled=true]
 * @property {number} [speed=10]
 * @property {number} [threshold=20]
 *
 * @typedef Position
 * @property {number} x
 * @property {number} y
 *
 * @typedef {DOMHelpers & {
 *  ctx: DraggableHookContext,
 *  addCleanup(cleanupFn: () => any): void,
 *  addEffectCleanup(cleanupFn: () => any): void,
 *  callHandler(handlerName: string, arg: Record<any, any>): void,
 * }} DraggableBuildHandlerParams
 *
 * @typedef {DOMHelpers & Position & { element: HTMLElement }} DraggableHandlerParams
 */

const DEFAULT_ACCEPTED_PARAMS = {
    enable: [Boolean, Function],
    ref: [Object],
    elements: [String],
    handle: [String, Function],
    ignore: [String, Function],
    cursor: [String],
    edgeScrolling: [Object, Function],
    tolerance: [Number],
};
const DEFAULT_DEFAULT_PARAMS = {
    enable: true,
    edgeScrolling: {
        speed: 10,
        threshold: 30,
    },
    tolerance: 10,
};
const DRAGGED_CLASS = "o_dragged";
const LEFT_CLICK = 0;
const MANDATORY_PARAMS = ["ref", "elements"];
const WHITE_LISTED_KEYS = ["Alt", "Control", "Meta", "Shift"];

/**
 * Cache containing the elements in which an attribute has been modified by a hook.
 * It is global since multiple draggable hooks can interact with the same elements.
 * @type {Record<string, Set<HTMLElement>>}
 */
const elCache = {};

/**
 * Transforms a camelCased string to return its kebab-cased version.
 * Typically used to generate CSS properties from JS objects.
 *
 * @param {string} str
 * @returns {string}
 */
function camelToKebab(str) {
    return str.replace(/([a-z])([A-Z])/g, "$1-$2").toLowerCase();
}

/**
 * @template T
 * @param {T | () => T} valueOrFn
 * @returns {T}
 */
function getReturnValue(valueOrFn) {
    if (typeof valueOrFn === "function") {
        return valueOrFn();
    }
    return valueOrFn;
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
 * @param {Function} [defaultCleanupFn]
 * @returns {CleanupManager}
 */
function makeCleanupManager(defaultCleanupFn) {
    /**
     * Registers the given cleanup function to be called when cleaning up hooks.
     * @param {Function} [cleanupFn]
     */
    const add = (cleanupFn) => typeof cleanupFn === "function" && cleanups.push(cleanupFn);

    /**
     * Runs all cleanup functions while clearing the cleanups list.
     */
    const cleanup = () => {
        while (cleanups.length) {
            cleanups.pop()();
        }
        add(defaultCleanupFn);
    };

    const cleanups = [];

    add(defaultCleanupFn);

    return { add, cleanup };
}

/**
 * @param {CleanupManager} cleanup
 * @returns {DOMHelpers}
 */
function makeDOMHelpers(cleanup) {
    /**
     * @param {HTMLElement} el
     * @param  {...string} classNames
     */
    const addClass = (el, ...classNames) => {
        if (!el || !classNames.length) {
            return;
        }
        cleanup.add(saveAttribute(el, "class"));
        el.classList.add(...classNames);
    };

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
        if (!el || !event || !callback) {
            return;
        }
        el.addEventListener(event, callback, options);
        if (/pointer|mouse/.test(event)) {
            // Restore pointer events on elements listening on mouse/pointer events.
            addStyle(el, { pointerEvents: "auto" });
        }
        cleanup.add(() => el.removeEventListener(event, callback, options));
    };

    /**
     * Adds style to an element to be cleaned up after the next drag sequence has
     * stopped.
     * @param {HTMLElement} el
     * @param {Record<string, string | number>} style
     */
    const addStyle = (el, style) => {
        if (!el || !style || !Object.keys(style).length) {
            return;
        }
        cleanup.add(saveAttribute(el, "style"));
        for (const key in style) {
            const [value, priority] = String(style[key]).split(/\s*!\s*/);
            el.style.setProperty(camelToKebab(key), value, priority);
        }
    };

    /**
     * Returns the bounding rect of the given element. If the `adjust` option is set
     * to true, the rect will be reduced by the padding of the element.
     * @param {HTMLElement} el
     * @param {Object} [options={}]
     * @param {boolean} [options.adjust=false]
     * @returns {DOMRect}
     */
    const getRect = (el, options = {}) => {
        if (!el) {
            return {};
        }
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
    };

    /**
     * @param {HTMLElement} el
     * @param  {...string} classNames
     */
    const removeClass = (el, ...classNames) => {
        if (!el || !classNames) {
            return;
        }
        cleanup.add(saveAttribute(el, "class"));
        el.classList.remove(...classNames);
    };

    /**
     * Adds style to an element to be cleaned up after the next drag sequence has
     * stopped.
     * @param {HTMLElement} el
     * @param {...string} properties
     */
    const removeStyle = (el, ...properties) => {
        if (!el || !properties?.length) {
            return;
        }
        cleanup.add(saveAttribute(el, "style"));
        for (const key of properties) {
            el.style.removeProperty(camelToKebab(key));
        }
    };

    return { addClass, addListener, addStyle, getRect, removeClass, removeStyle };
}

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 * @param {string} val
 * @returns {number}
 */
function pixelValueToNumber(val) {
    return Number(val.endsWith("px") ? val.slice(0, -2) : val);
}

function saveAttribute(el, attribute) {
    const restoreAttribute = () => {
        cache.delete(el);
        if (originalValue) {
            el.setAttribute(attribute, originalValue);
        } else {
            el.removeAttribute(attribute);
        }
    };

    if (!(attribute in elCache)) {
        elCache[attribute] = new Set();
    }
    const cache = elCache[attribute];

    if (cache.has(el)) {
        return;
    }

    cache.add(el);
    const originalValue = el.getAttribute(attribute);

    return restoreAttribute;
}

/**
 * @template T
 * @param {T | () => T} value
 * @returns {() => T}
 */
function toFunction(value) {
    return typeof value === "function" ? value : () => value;
}

/**
 * @param {DraggableBuilderParams} hookParams
 * @returns {(params: Record<any, any>) => { dragging: boolean }}
 */
export function makeDraggableHook(hookParams) {
    hookParams = getReturnValue(hookParams);

    const hookName = hookParams.name || "useAnonymousDraggable";
    const allAcceptedParams = { ...DEFAULT_ACCEPTED_PARAMS, ...hookParams.acceptedParams };
    const defaultParams = { ...DEFAULT_DEFAULT_PARAMS, ...hookParams.defaultParams };

    /**
     * Computes the current params and converts the params definition
     * @param {SortableParams} params
     * @returns {[string, string | boolean][]}
     */
    const computeParams = (params) => {
        const computedParams = { enable: () => true };
        for (const prop in allAcceptedParams) {
            if (prop in params) {
                if (prop === "enable") {
                    computedParams[prop] = toFunction(params[prop]);
                } else if (
                    allAcceptedParams[prop].length === 1 &&
                    allAcceptedParams[prop][0] === Function
                ) {
                    computedParams[prop] = params[prop];
                } else {
                    computedParams[prop] = getReturnValue(params[prop]);
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
             * Executes a handler from the `hookParams`.
             * @param {string} hookHandlerName
             * @param {Record<any, any>} arg
             */
            const callBuildHandler = (hookHandlerName, arg) => {
                if (typeof hookParams[hookHandlerName] !== "function") {
                    return;
                }
                const returnValue = hookParams[hookHandlerName]({ ctx, ...helpers, ...arg });
                if (returnValue) {
                    callHandler(hookHandlerName, returnValue);
                }
            };

            /**
             * Safely executes a handler from the `params`, so that the drag sequence can
             * be interrupted if an error occurs.
             * @param {string} handlerName
             * @param {Record<any, any>} arg
             */
            const callHandler = (handlerName, arg) => {
                if (typeof params[handlerName] !== "function") {
                    return;
                }
                try {
                    params[handlerName]({ ...dom, ...ctx.mouse, ...arg });
                } catch (err) {
                    dragEnd(null, true);
                    throw err;
                }
            };

            /**
             * Returns whether the user has moved from at least the number of pixels
             * that are tolerated from the initial mouse position.
             */
            const canStartDrag = () => {
                const {
                    mouse,
                    current: { initialPosition },
                } = ctx;
                return (
                    !ctx.tolerance ||
                    Math.hypot(mouse.x - initialPosition.x, mouse.y - initialPosition.y) >=
                        ctx.tolerance
                );
            };

            /**
             * Main entry function to start a drag sequence.
             */
            const dragStart = () => {
                state.dragging = true;

                // Compute scrollable parent
                ctx.current.scrollParent = getScrollParent(ctx.current.container);

                updateRects();
                const { x, y, width, height } = ctx.current.elementRect;

                // Adjusts the offset
                ctx.current.offset = {
                    x: ctx.current.initialPosition.x - x,
                    y: ctx.current.initialPosition.y - y,
                };

                if (ctx.followCursor) {
                    dom.addStyle(ctx.current.element, {
                        width: `${width}px`,
                        height: `${height}px`,
                        position: "fixed !important",
                    });

                    // First adjustment
                    updateElementPosition();
                }

                dom.addStyle(document.body, {
                    pointerEvents: "none",
                    userSelect: "none",
                });
                if (ctx.cursor) {
                    dom.addStyle(document.body, { cursor: ctx.cursor });
                }

                if (ctx.current.scrollParent && ctx.edgeScrolling.enabled) {
                    const cleanupFn = setRecurringAnimationFrame(handleEdgeScrolling);
                    cleanup.add(cleanupFn);
                }

                dom.addClass(ctx.current.element, DRAGGED_CLASS);

                callBuildHandler("onDragStart");
            };

            /**
             * Main exit function to stop a drag sequence. Note that it can be called
             * even if a drag sequence did not start yet to perform a cleanup of all
             * current context variables.
             * @param {HTMLElement | null} target
             * @param {boolean} [inErrorState] can be set to true when an error
             *  occurred to avoid falling into an infinite loop if the error
             *  originated from one of the handlers.
             */
            const dragEnd = (target, inErrorState) => {
                if (state.dragging) {
                    if (!inErrorState) {
                        if (target) {
                            callBuildHandler("onDrop", { target });
                        }
                        callBuildHandler("onDragEnd");
                    }
                }

                cleanup.cleanup();
            };

            /**
             * Applies scroll to the container if the current element is near
             * the edge of the container.
             */
            const handleEdgeScrolling = (deltaTime) => {
                updateRects();
                const eRect = ctx.current.elementRect;
                const cRect = ctx.current.containerRect;

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

                if (diff.x && !diff.x[0]) {
                    delete diff.x;
                }
                if (diff.y && !diff.y[0]) {
                    delete diff.y;
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
                    ctx.current.scrollParent.scrollBy(scrollParams);
                }
            };

            /**
             * Window "keydown" event handler.
             * @param {KeyboardEvent} ev
             */
            const onKeyDown = (ev) => {
                if (!state.dragging || !ctx.enable()) {
                    return;
                }
                if (!WHITE_LISTED_KEYS.includes(ev.key)) {
                    ev.stopImmediatePropagation();
                    ev.preventDefault();

                    // Cancels drag sequences on every non-whitelisted key down event.
                    dragEnd(null);
                }
            };

            /**
             * Global (= ref) "mousedown" event handler.
             * @param {MouseEvent} ev
             */
            const onMouseDown = (ev) => {
                updateMousePosition(ev);

                // A drag sequence can still be in progress if the mouseup occurred
                // outside of the window.
                dragEnd(null);

                if (
                    ev.button !== LEFT_CLICK ||
                    !ctx.enable() ||
                    !ev.target.closest(ctx.fullSelector) ||
                    (ctx.ignoreSelector && ev.target.closest(ctx.ignoreSelector))
                ) {
                    return;
                }

                // In FireFox: elements with `overflow: hidden` will prevent mouseenter and mouseleave
                // events from firing on elements underneath them. This is the case when dragging a card
                // by the `.o_kanban_record_headings` element. In such cases, we can prevent the default
                // action on the mousedown event to allow mouse events to fire properly.
                // https://bugzilla.mozilla.org/show_bug.cgi?id=1352061
                // https://bugzilla.mozilla.org/show_bug.cgi?id=339293
                ev.preventDefault();

                const { target } = ev;
                ctx.current.initialPosition = { ...ctx.mouse };

                willStartDrag(target);
            };

            /**
             * Window "mousemove" event handler.
             * @param {MouseEvent} ev
             */
            const onMouseMove = (ev) => {
                updateMousePosition(ev);

                if (!ctx.current.element || !ctx.enable()) {
                    return;
                }

                ev.preventDefault();

                if (!state.dragging) {
                    if (!canStartDrag()) {
                        return;
                    }
                    dragStart();
                }

                if (ctx.followCursor) {
                    updateElementPosition();
                }

                callBuildHandler("onDrag");
            };

            /**
             * Window "mouseup" event handler.
             * @param {MouseEvent} ev
             */
            const onMouseUp = (ev) => {
                updateMousePosition(ev);
                dragEnd(ev.target);
            };

            /**
             * Updates the position of the current dragged element according to
             * the current mouse position.
             */
            const updateElementPosition = () => {
                const { containerRect, element, elementRect, offset } = ctx.current;
                const { width: ew, height: eh } = elementRect;
                const { x: cx, y: cy, width: cw, height: ch } = containerRect;

                // Updates the position of the dragged element.
                dom.addStyle(element, {
                    left: `${clamp(ctx.mouse.x - offset.x, cx, cx + cw - ew)}px`,
                    top: `${clamp(ctx.mouse.y - offset.y, cy, cy + ch - eh)}px`,
                });
            };

            /**
             * Updates the current mouse position from a given event.
             * @param {MouseEvent} ev
             */
            const updateMousePosition = (ev) => {
                ctx.mouse.x = ev.clientX;
                ctx.mouse.y = ev.clientY;
            };

            const updateRects = () => {
                const { current } = ctx;
                const { container, element, scrollParent } = current;
                // Container rect
                current.containerRect = dom.getRect(container, { adjust: true });
                if (scrollParent && ctx.edgeScrolling.enabled) {
                    // Adjust container rect according to scrollparent
                    const parentRect = dom.getRect(scrollParent, { adjust: true });
                    current.containerRect.x = Math.max(current.containerRect.x, parentRect.x);
                    current.containerRect.y = Math.max(current.containerRect.y, parentRect.y);
                    current.containerRect.width = Math.min(
                        current.containerRect.width,
                        parentRect.width
                    );
                    current.containerRect.height = Math.min(
                        current.containerRect.height,
                        parentRect.height
                    );
                }

                // Element rect
                ctx.current.elementRect = dom.getRect(element);
            };

            /**
             * @param {Element} target
             */
            const willStartDrag = (target) => {
                ctx.current.element = target.closest(ctx.elementSelector);
                ctx.current.container = ctx.ref.el;

                cleanup.add(() => (ctx.current = {}));

                callBuildHandler("onWillStartDrag");
            };

            // Initialize helpers
            const cleanup = makeCleanupManager(() => (state.dragging = false));
            const effectCleanup = makeCleanupManager();
            const dom = makeDOMHelpers(cleanup);

            const helpers = {
                ...dom,
                addCleanup: cleanup.add,
                addEffectCleanup: effectCleanup.add,
                callHandler,
            };

            // Component infos
            const state = reactive({ dragging: false });

            // Basic error handling asserting that the parameters are valid.
            for (const prop in allAcceptedParams) {
                const type = typeof params[prop];
                const acceptedTypes = allAcceptedParams[prop].map((t) => t.name.toLowerCase());
                if (params[prop]) {
                    if (!acceptedTypes.includes(type)) {
                        throw makeError(
                            `invalid type for property "${prop}" in parameters: expected { ${acceptedTypes.join(
                                ", "
                            )} } and got ${type}`
                        );
                    }
                } else if (MANDATORY_PARAMS.includes(prop)) {
                    throw makeError(`missing required property "${prop}" in parameters`);
                }
            }

            /** @type {DraggableHookContext} */
            const ctx = {
                enable: () => false,
                ref: params.ref,
                ignoreSelector: null,
                fullSelector: null,
                followCursor: true,
                cursor: null,
                mouse: { x: 0, y: 0 },
                edgeScrolling: { enabled: true },
                get dragging() {
                    return state.dragging;
                },
                // Current context
                current: {},
            };

            // Effect depending on the params to update them.
            useEffect(
                (...deps) => {
                    const actualParams = { ...defaultParams, ...Object.fromEntries(deps) };
                    if (!ctx.ref.el) {
                        return;
                    }

                    // Enable getter
                    ctx.enable = actualParams.enable;

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

                    // Edge scrolling
                    Object.assign(ctx.edgeScrolling, actualParams.edgeScrolling);

                    // Delay & tolerance
                    ctx.tolerance = actualParams.tolerance;

                    callBuildHandler("onComputeParams", { params: actualParams });

                    // Calls effect cleanup functions when preparing to re-render.
                    return effectCleanup.cleanup;
                },
                () => computeParams(params)
            );
            // Effect depending on the `ref.el` to add triggering mouse events listener.
            useEffect(
                (el) => {
                    if (el) {
                        el.addEventListener("mousedown", onMouseDown);
                        return () => el.removeEventListener("mousedown", onMouseDown);
                    }
                },
                () => [ctx.ref.el]
            );
            // Other global event listeners.
            const throttledOnMouseMove = useThrottleForAnimation(onMouseMove);
            useExternalListener(window, "mousemove", throttledOnMouseMove);
            useExternalListener(window, "mouseup", onMouseUp);
            useExternalListener(window, "keydown", onKeyDown, true);
            onWillUnmount(() => dragEnd(null));

            return state;
        },
    }[hookName];
}
