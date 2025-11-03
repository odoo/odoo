import { clamp } from "@web/core/utils/numbers";
import { omit } from "@web/core/utils/objects";
import { closestScrollableX, closestScrollableY } from "@web/core/utils/scrolling";
import { setRecurringAnimationFrame } from "@web/core/utils/timing";
import { browser } from "../browser/browser";
import { hasTouch, isBrowserFirefox, isIOS } from "../browser/feature_detection";

/**
 * @typedef {ReturnType<typeof makeCleanupManager>} CleanupManager
 *
 * @typedef {ReturnType<typeof makeDOMHelpers>} DOMHelpers
 *
 * @typedef DraggableBuilderParams
 * Hook params
 * @property {string} [name="useAnonymousDraggable"]
 * @property {EdgeScrollingOptions} [edgeScrolling]
 * @property {Record<string, string[]>} [acceptedParams]
 * @property {Record<string, any>} [defaultParams]
 * Setup hooks
 * @property {{
 *  addListener: typeof import("@odoo/owl")["useExternalListener"];
 *  setup: typeof import("@odoo/owl")["useEffect"];
 *  teardown: typeof import("@odoo/owl")["onWillUnmount"];
 *  throttle: typeof import("./timing")["useThrottleForAnimation"];
 *  wrapState: typeof import("@odoo/owl")["reactive"];
 * }} setupHooks
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
 * @property {(HTMLElement) => boolean} [preventDrag=(el) => false]
 * @property {Position} [pointer={ x: 0, y: 0 }]
 * @property {EdgeScrollingOptions} [edgeScrolling]
 * @property {number} [delay]
 * @property {number} [tolerance]
 * @property {DraggableHookCurrentContext} current
 *
 * @typedef DraggableHookCurrentContext
 * @property {HTMLElement} [current.container]
 * @property {DOMRect} [current.containerRect]
 * @property {HTMLElement} [current.element]
 * @property {DOMRect} [current.elementRect]
 * @property {HTMLElement | null} [current.scrollParentX]
 * @property {DOMRect | null} [current.scrollParentXRect]
 * @property {HTMLElement | null} [current.scrollParentY]
 * @property {DOMRect | null} [current.scrollParentYRect]
 * @property {"left"|"right"|"top"|"bottom"|null} [scrollingEdge]
 * @property {number} [timeout]
 * @property {Position} [initialPosition]
 * @property {Position} [offset={ x: 0, y: 0 }]
 *
 * @typedef EdgeScrollingOptions
 * @property {boolean} [enabled=true]
 * @property {number} [speed=10]
 * @property {number} [threshold=20]
 * @property {"horizontal"|"vertical"} [direction]
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

const DRAGGABLE_CLASS = "o_draggable";
export const DRAGGED_CLASS = "o_dragged";

const DEFAULT_ACCEPTED_PARAMS = {
    enable: [Boolean, Function],
    preventDrag: [Function],
    ref: [Object],
    elements: [String],
    handle: [String, Function],
    ignore: [String, Function],
    cursor: [String],
    edgeScrolling: [Object, Function],
    delay: [Number],
    tolerance: [Number],
    touchDelay: [Number],
    iframeWindow: [Object, Function],
};
const DEFAULT_DEFAULT_PARAMS = {
    elements: `.${DRAGGABLE_CLASS}`,
    enable: true,
    preventDrag: () => false,
    edgeScrolling: {
        speed: 10,
        threshold: 30,
    },
    delay: 0,
    tolerance: 10,
    touchDelay: 300,
};
const LEFT_CLICK = 0;
const MANDATORY_PARAMS = ["ref"];
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
 * @returns {(HTMLElement | null)[]}
 */
function getScrollParents(el) {
    return [closestScrollableX(el), closestScrollableY(el)];
}

/**
 * @param {() => any} [defaultCleanupFn]
 */
function makeCleanupManager(defaultCleanupFn) {
    /**
     * Registers the given cleanup function to be called when cleaning up hooks.
     * @param {() => any} [cleanupFn]
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
        cleanup.add(() => el.classList.remove(...classNames));
        el.classList.add(...classNames);
    };

    /**
     * Adds an event listener to be cleaned up after the next drag sequence
     * has stopped.
     * @param {EventTarget} el
     * @param {string} event
     * @param {(...args: any[]) => any} callback
     * @param {AddEventListenerOptions & { noAddedStyle?: boolean }} [options]
     */
    const addListener = (el, event, callback, options = {}) => {
        if (!el || !event || !callback) {
            return;
        }
        const { noAddedStyle } = options;
        delete options.noAddedStyle;
        el.addEventListener(event, callback, options);
        if (!noAddedStyle && /mouse|pointer|touch/.test(event)) {
            // Restore pointer events on elements listening on mouse/pointer/touch events.
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

        rect.height = el.offsetHeight;

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
     * @param {string} attribute
     */
    const removeAttribute = (el, attribute) => {
        if (!el || !attribute) {
            return;
        }
        cleanup.add(saveAttribute(el, attribute));
        el.removeAttribute(attribute);
    };

    /**
     * @param {HTMLElement} el
     * @param {...string} classNames
     */
    const removeClass = (el, ...classNames) => {
        if (!el || !classNames.length) {
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
        if (!el || !properties.length) {
            return;
        }
        cleanup.add(saveAttribute(el, "style"));
        for (const key of properties) {
            el.style.removeProperty(camelToKebab(key));
        }
    };

    /**
     * @param {HTMLElement} el
     * @param {string} attribute
     * @param {any} value
     */
    const setAttribute = (el, attribute, value) => {
        if (!el || !attribute) {
            return;
        }
        cleanup.add(saveAttribute(el, attribute));
        el.setAttribute(attribute, String(value));
    };

    return {
        addClass,
        addListener,
        addStyle,
        getRect,
        removeAttribute,
        removeClass,
        removeStyle,
        setAttribute,
    };
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
 * @param {Event} ev
 * @param {{ stop?: boolean }} params
 */
function safePrevent(ev, { stop } = {}) {
    if (ev.cancelable) {
        ev.preventDefault();
        if (stop) {
            ev.stopPropagation();
        }
    }
}

function saveAttribute(el, attribute) {
    const restoreAttribute = () => {
        cache.delete(el);
        if (hasAttribute) {
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
    const hasAttribute = el.hasAttribute(attribute);
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
 * @returns {(params: Record<keyof typeof DEFAULT_ACCEPTED_PARAMS, any>) => { dragging: boolean }}
 */
export function makeDraggableHook(hookParams) {
    hookParams = getReturnValue(hookParams);

    const hookName = hookParams.name || "useAnonymousDraggable";
    const { setupHooks } = hookParams;
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
    let preventClick = false;

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
                    params[handlerName]({ ...dom, ...ctx.pointer, ...arg });
                } catch (err) {
                    dragEnd(null, true);
                    throw err;
                }
            };

            /**
             * Returns whether the user has moved from at least the number of pixels
             * that are tolerated from the initial pointer position.
             */
            const canStartDrag = () => {
                const {
                    pointer,
                    current: { initialPosition },
                } = ctx;
                return (
                    !ctx.tolerance ||
                    Math.hypot(pointer.x - initialPosition.x, pointer.y - initialPosition.y) >=
                        ctx.tolerance
                );
            };

            /**
             * Main entry function to start a drag sequence.
             */
            const dragStart = () => {
                state.dragging = true;
                state.willDrag = false;

                // Compute scrollable parent
                const isDocumentScrollingElement =
                    ctx.current.container === ctx.current.container.ownerDocument.scrollingElement;
                // If the container is the "ownerDocument.scrollingElement",
                // there is no need to get the scroll parent as it is the
                // scrollable element itself.
                // TODO: investigate if "getScrollParents" should not consider
                // the "ownerDocument.scrollingElement" directly.
                [ctx.current.scrollParentX, ctx.current.scrollParentY] = isDocumentScrollingElement
                    ? [ctx.current.container, ctx.current.container]
                    : getScrollParents(ctx.current.container);

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

                dom.addClass(document.body, "pe-none", "user-select-none");
                if (params.iframeWindow) {
                    for (const iframe of document.getElementsByTagName("iframe")) {
                        if (iframe.contentWindow === params.iframeWindow) {
                            dom.addClass(iframe, "pe-none", "user-select-none");
                        }
                    }
                }
                // FIXME: adding pe-none and cursor on the same element makes
                // no sense as pe-none prevents the cursor to be displayed.
                if (ctx.cursor) {
                    dom.addStyle(document.body, { cursor: ctx.cursor });
                }

                if (
                    (ctx.current.scrollParentX || ctx.current.scrollParentY) &&
                    ctx.edgeScrolling.enabled
                ) {
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
                    preventClick = true;
                    if (!inErrorState) {
                        if (target && ctx.current.element.isConnected) {
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
                const { x: pointerX, y: pointerY } = ctx.pointer;
                const xRect = ctx.current.scrollParentXRect;
                const yRect = ctx.current.scrollParentYRect;

                // "getBoundingClientRect()"" (used in "getRect()") gives the
                // distance from the element's top to the viewport, excluding
                // scroll position. Only the "document.scrollingElement" element
                // ("<html>") accounts for scrollTop.
                const scrollParentYEl = ctx.current.scrollParentY;
                if (scrollParentYEl === ctx.current.container.ownerDocument.scrollingElement) {
                    yRect.y += scrollParentYEl.scrollTop;
                }

                const { direction, speed, threshold } = ctx.edgeScrolling;
                const correctedSpeed = (speed / 16) * deltaTime;

                const diff = {};
                ctx.current.scrollingEdge = null;
                if (xRect) {
                    const maxWidth = xRect.x + xRect.width;
                    if (pointerX - xRect.x < threshold) {
                        diff.x = [pointerX - xRect.x, -1];
                        ctx.current.scrollingEdge = "left";
                    } else if (maxWidth - pointerX < threshold) {
                        diff.x = [maxWidth - pointerX, 1];
                        ctx.current.scrollingEdge = "right";
                    }
                }
                if (yRect) {
                    const maxHeight = yRect.y + yRect.height;
                    if (pointerY - yRect.y < threshold) {
                        diff.y = [pointerY - yRect.y, -1];
                        ctx.current.scrollingEdge = "top";
                    } else if (maxHeight - pointerY < threshold) {
                        diff.y = [maxHeight - pointerY, 1];
                        ctx.current.scrollingEdge = "bottom";
                    }
                }

                const diffToScroll = ([delta, sign]) =>
                    (1 - Math.max(delta, 0) / threshold) * correctedSpeed * sign;
                if ((!direction || direction === "vertical") && diff.y) {
                    ctx.current.scrollParentY.scrollBy({ top: diffToScroll(diff.y) });
                }
                if ((!direction || direction === "horizontal") && diff.x) {
                    ctx.current.scrollParentX.scrollBy({ left: diffToScroll(diff.x) });
                }
                callBuildHandler("onDrag");
            };

            /**
             * Global (= ref) "click" event handler.
             * Used to prevent click events after dragEnd
             * @param {PointerEvent} ev
             */
            const onClick = (ev) => {
                if (preventClick) {
                    safePrevent(ev, { stop: true });
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
                    safePrevent(ev, { stop: true });

                    // Cancels drag sequences on every non-whitelisted key down event.
                    dragEnd(null);
                }
            };

            /**
             * Global (= ref) "pointercancel" event handler.
             */
            const onPointerCancel = () => {
                dragEnd(null);
            };

            /**
             * Global (= ref) "pointerdown" event handler.
             * @param {PointerEvent} ev
             */
            const onPointerDown = (ev) => {
                preventClick = false;
                updatePointerPosition(ev);

                const initiationDelay = ev.pointerType === "touch" ? ctx.touchDelay : ctx.delay;

                // A drag sequence can still be in progress if the pointerup occurred
                // outside of the window.
                dragEnd(null);

                const fullSelectorEl = ev.target.closest(ctx.fullSelector);
                if (
                    ev.button !== LEFT_CLICK ||
                    !ctx.enable() ||
                    !fullSelectorEl ||
                    (ctx.ignoreSelector && ev.target.closest(ctx.ignoreSelector)) ||
                    ctx.preventDrag(fullSelectorEl)
                ) {
                    return;
                }

                // In FireFox: elements with `overflow: hidden` will prevent mouseenter and mouseleave
                // events from firing on elements underneath them. This is the case when dragging a card
                // by the heading. In such cases, we can prevent the default
                // action on the pointerdown event to allow pointer events to fire properly.
                // https://bugzilla.mozilla.org/show_bug.cgi?id=1352061
                // https://bugzilla.mozilla.org/show_bug.cgi?id=339293
                safePrevent(ev);
                let activeElement = document.activeElement;
                while (activeElement?.nodeName === "IFRAME") {
                    activeElement = activeElement.contentDocument?.activeElement;
                }
                if (activeElement && !activeElement.contains(ev.target)) {
                    activeElement.blur();
                }

                const { currentTarget, pointerId, target } = ev;
                ctx.current.initialPosition = { ...ctx.pointer };

                if (target.hasPointerCapture(pointerId)) {
                    target.releasePointerCapture(pointerId);
                }

                if (initiationDelay) {
                    if (hasTouch()) {
                        if (ev.pointerType === "touch") {
                            dom.addClass(target.closest(ctx.elementSelector), "o_touch_bounce");
                        }
                        if (isBrowserFirefox()) {
                            // On Firefox mobile, long-touch events trigger an unpreventable
                            // context menu to appear. To prevent this, all linkes are removed
                            // from the dragged elements during the drag sequence.
                            const links = [...currentTarget.querySelectorAll("[href]")];
                            if (currentTarget.hasAttribute("href")) {
                                links.unshift(currentTarget);
                            }
                            for (const link of links) {
                                dom.removeAttribute(link, "href");
                            }
                        }
                        if (isIOS()) {
                            // On Safari mobile, any image can be dragged regardless
                            // of the 'user-select' property.
                            for (const image of currentTarget.getElementsByTagName("img")) {
                                dom.setAttribute(image, "draggable", false);
                            }
                        }
                    }

                    ctx.current.timeout = browser.setTimeout(() => {
                        ctx.current.initialPosition = { ...ctx.pointer };

                        willStartDrag(target);

                        const { x: px, y: py } = ctx.pointer;
                        const { x, y, width, height } = dom.getRect(ctx.current.element);
                        if (px < x || x + width < px || py < y || y + height < py) {
                            // Pointer left the target
                            // Note that the timeout is cleared in dragEnd
                            dragEnd(null);
                        }
                    }, initiationDelay);
                    cleanup.add(() => browser.clearTimeout(ctx.current.timeout));
                } else {
                    willStartDrag(target);
                }
            };

            /**
             * Window "pointermove" event handler.
             * @param {PointerEvent} ev
             */
            const onPointerMove = (ev) => {
                updatePointerPosition(ev);

                if (!ctx.current.element || !ctx.enable()) {
                    return;
                }

                safePrevent(ev);

                if (!state.dragging) {
                    if (!canStartDrag()) {
                        return;
                    }
                    dragStart();
                } else if (!ctx.current.element.isConnected) {
                    return dragEnd(null);
                }

                if (ctx.followCursor) {
                    updateElementPosition();
                }

                callBuildHandler("onDrag");
            };

            /**
             * Window "pointerup" event handler.
             * @param {PointerEvent} ev
             */
            const onPointerUp = (ev) => {
                updatePointerPosition(ev);
                dragEnd(ev.target);
            };

            /**
             * Updates the position of the current dragged element according to
             * the current pointer position.
             */
            const updateElementPosition = () => {
                const { containerRect, element, elementRect, offset } = ctx.current;
                const { width: ew, height: eh } = elementRect;
                const { x: cx, y: cy, width: cw, height: ch } = containerRect;

                // Updates the position of the dragged element.
                dom.addStyle(element, {
                    left: `${clamp(ctx.pointer.x - offset.x, cx, cx + cw - ew)}px`,
                    top: `${clamp(ctx.pointer.y - offset.y, cy, cy + ch - eh)}px`,
                });
            };

            /**
             * Updates the current pointer position from a given event.
             * @param {PointerEvent} ev
             */
            const updatePointerPosition = (ev) => {
                ctx.pointer.x = ev.clientX;
                ctx.pointer.y = ev.clientY;
            };

            const updateRects = () => {
                const { current } = ctx;
                const { container, element, scrollParentX, scrollParentY } = current;
                // Container rect
                current.containerRect = dom.getRect(container, { adjust: true });
                // If the scrolling element is within an iframe and the draggable
                // element is outside this iframe, the offsets must be computed taking
                // into account the iframe.
                let iframeOffsetX = 0;
                let iframeOffsetY = 0;
                const iframeEl = container.ownerDocument.defaultView.frameElement;
                if (iframeEl && !iframeEl.contentDocument?.contains(element)) {
                    const { x, y } = dom.getRect(iframeEl);
                    iframeOffsetX = x;
                    iframeOffsetY = y;
                    current.containerRect.x += iframeOffsetX;
                    current.containerRect.y += iframeOffsetY;
                }
                // Adjust container rect according to its overflowing size
                current.containerRect.width = container.scrollWidth;
                current.containerRect.height = container.scrollHeight;
                // ScrollParent rect
                current.scrollParentXRect = null;
                current.scrollParentYRect = null;
                if (ctx.edgeScrolling.enabled) {
                    // Adjust container rect according to scrollParents
                    if (scrollParentX) {
                        current.scrollParentXRect = dom.getRect(scrollParentX, { adjust: true });
                        current.scrollParentXRect.x += iframeOffsetX;
                        current.scrollParentXRect.y += iframeOffsetY;
                        const right = Math.min(
                            current.containerRect.left + container.scrollWidth,
                            current.scrollParentXRect.right
                        );
                        current.containerRect.x = Math.max(
                            current.containerRect.x,
                            current.scrollParentXRect.x
                        );
                        current.containerRect.width = right - current.containerRect.x;
                    }
                    if (scrollParentY) {
                        current.scrollParentYRect = dom.getRect(scrollParentY, { adjust: true });
                        current.scrollParentYRect.x += iframeOffsetX;
                        current.scrollParentYRect.y += iframeOffsetY;
                        const bottom = Math.min(
                            current.containerRect.top + container.scrollHeight,
                            current.scrollParentYRect.bottom
                        );
                        current.containerRect.y = Math.max(
                            current.containerRect.y,
                            current.scrollParentYRect.y
                        );
                        current.containerRect.height = bottom - current.containerRect.y;
                    }
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
                state.willDrag = true;

                callBuildHandler("onWillStartDrag");

                if (hasTouch()) {
                    // Prevents panning/zooming after a long press
                    dom.addListener(window, "touchmove", safePrevent, {
                        passive: false,
                        noAddedStyle: true,
                    });
                    if (params.iframeWindow) {
                        dom.addListener(params.iframeWindow, "touchmove", safePrevent, {
                            passive: false,
                            noAddedStyle: true,
                        });
                    }
                }
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
            const state = setupHooks.wrapState({ dragging: false });

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
                } else if (MANDATORY_PARAMS.includes(prop) && !defaultParams[prop]) {
                    throw makeError(`missing required property "${prop}" in parameters`);
                }
            }

            /** @type {DraggableHookContext} */
            const ctx = {
                enable: () => false,
                preventDrag: () => false,
                ref: params.ref,
                ignoreSelector: null,
                fullSelector: null,
                followCursor: true,
                cursor: null,
                pointer: { x: 0, y: 0 },
                edgeScrolling: { enabled: true },
                get dragging() {
                    return state.dragging;
                },
                get willDrag() {
                    return state.willDrag;
                },
                // Current context
                current: {},
            };

            // Effect depending on the params to update them.
            setupHooks.setup(
                (...deps) => {
                    const params = Object.fromEntries(deps);
                    const actualParams = { ...defaultParams, ...omit(params, "edgeScrolling") };
                    if (params.edgeScrolling) {
                        actualParams.edgeScrolling = {
                            ...actualParams.edgeScrolling,
                            ...params.edgeScrolling,
                        };
                    }

                    if (!ctx.ref.el) {
                        return;
                    }

                    // Enable getter
                    ctx.enable = actualParams.enable;

                    // Dragging constraint
                    if (actualParams.preventDrag) {
                        ctx.preventDrag = actualParams.preventDrag;
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

                    // Edge scrolling
                    Object.assign(ctx.edgeScrolling, actualParams.edgeScrolling);

                    // Delay & tolerance
                    ctx.delay = actualParams.delay;
                    ctx.touchDelay = actualParams.delay || actualParams.touchDelay;
                    ctx.tolerance = actualParams.tolerance;

                    callBuildHandler("onComputeParams", { params: actualParams });

                    // Calls effect cleanup functions when preparing to re-render.
                    return effectCleanup.cleanup;
                },
                () => computeParams(params)
            );
            // Firefox currently (119.0.1) does not handle our pointer events
            // nicely when they happen from within the iframe. To work around
            // this, we use mouse events instead of pointer events.
            const useMouseEvents = isBrowserFirefox() && !hasTouch() && params.iframeWindow;
            // Effect depending on the `ref.el` to add triggering pointer events listener.
            setupHooks.setup(
                (el) => {
                    if (el) {
                        const { add, cleanup } = makeCleanupManager();
                        const { addListener } = makeDOMHelpers({ add });
                        const event = useMouseEvents ? "mousedown" : "pointerdown";
                        addListener(el, event, onPointerDown, { noAddedStyle: true });
                        addListener(el, "click", onClick);
                        if (hasTouch()) {
                            addListener(el, "contextmenu", safePrevent);
                            // Adds a non-passive listener on touchstart: this allows
                            // the subsequent "touchmove" events to be cancelable
                            // and thus prevent parasitic "touchcancel" events to
                            // be fired. Note that we DO NOT want to prevent touchstart
                            // events since they're responsible of the native swipe
                            // scrolling.
                            addListener(el, "touchstart", () => {}, {
                                passive: false,
                                noAddedStyle: true,
                            });
                        }
                        return cleanup;
                    }
                },
                () => [ctx.ref.el]
            );
            const addWindowListener = (type, listener, options) => {
                if (params.iframeWindow) {
                    setupHooks.addListener(params.iframeWindow, type, listener, options);
                }
                setupHooks.addListener(window, type, listener, options);
            };
            // Other global event listeners.
            const throttledOnPointerMove = setupHooks.throttle(onPointerMove);
            addWindowListener(
                useMouseEvents ? "mousemove" : "pointermove",
                throttledOnPointerMove,
                { passive: false }
            );
            addWindowListener(useMouseEvents ? "mouseup" : "pointerup", onPointerUp);
            addWindowListener("pointercancel", onPointerCancel);
            addWindowListener("keydown", onKeyDown, { capture: true });
            setupHooks.teardown(() => dragEnd(null));

            return state;
        },
    }[hookName];
}
