// @ts-check

/** @module @web/core/utils/dnd/draggable_hook_builder - Factory for configurable drag-and-drop OWL hooks with touch and scroll support */

import { browser } from "@web/core/browser/browser";
import { hasTouch, isBrowserFirefox, isIOS } from "@web/core/browser/feature_detection";
import { omit } from "@web/core/utils/collections/objects";
import { clamp } from "@web/core/utils/format/numbers";
import { setRecurringAnimationFrame } from "@web/core/utils/timing";

import {
    DEFAULT_ACCEPTED_PARAMS,
    DEFAULT_DEFAULT_PARAMS,
    DRAGGED_CLASS,
    getReturnValue,
    getScrollParents,
    LEFT_CLICK,
    makeCleanupManager,
    makeDOMHelpers,
    MANDATORY_PARAMS,
    safePrevent,
    toFunction,
    WHITE_LISTED_KEYS,
} from "./draggable_hook_builder_utils";

export { DRAGGED_CLASS };

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
 *  throttle: typeof import("@web/core/utils/timing")["useThrottleForAnimation"];
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
 * @typedef {{
 *  ref: { el: HTMLElement | null };
 *  elementSelector?: string | null;
 *  ignoreSelector?: string | null;
 *  fullSelector?: string | null;
 *  followCursor?: boolean;
 *  cursor?: string | null;
 *  enable?: () => boolean;
 *  preventDrag?: (el: HTMLElement) => boolean;
 *  pointer?: Position;
 *  edgeScrolling?: EdgeScrollingOptions;
 *  delay?: number;
 *  tolerance?: number;
 *  touchDelay?: number;
 *  dragging?: boolean;
 *  willDrag?: boolean;
 *  current: DraggableHookCurrentContext;
 *  [key: string]: any;
 * }} DraggableHookContext
 *
 * @typedef {{
 *  container?: HTMLElement;
 *  containerRect?: DOMRect;
 *  element?: HTMLElement;
 *  elementRect?: DOMRect;
 *  scrollParentX?: HTMLElement | null;
 *  scrollParentXRect?: DOMRect | null;
 *  scrollParentY?: HTMLElement | null;
 *  scrollParentYRect?: DOMRect | null;
 *  scrollingEdge?: "left"|"right"|"top"|"bottom"|null;
 *  timeout?: number;
 *  initialPosition?: Position;
 *  offset?: Position;
 *  [key: string]: any;
 * }} DraggableHookCurrentContext
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

/**
 * @param {DraggableBuilderParams} hookParams
 * @returns {(params: Record<keyof typeof DEFAULT_ACCEPTED_PARAMS, any>) => { dragging: boolean }}
 */
export function makeDraggableHook(hookParams) {
    hookParams = getReturnValue(hookParams);

    const hookName = hookParams.name || "useAnonymousDraggable";
    const { setupHooks } = hookParams;
    const allAcceptedParams = {
        ...DEFAULT_ACCEPTED_PARAMS,
        ...hookParams.acceptedParams,
    };
    const defaultParams = {
        ...DEFAULT_DEFAULT_PARAMS,
        ...hookParams.defaultParams,
    };

    /**
     * Computes the current params and converts the params definition
     * @param {Record<string, any>} params
     * @returns {[string, any][]}
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
             * @param {Record<any, any>} [arg]
             */
            const callBuildHandler = (hookHandlerName, arg = {}) => {
                if (typeof hookParams[hookHandlerName] !== "function") {
                    return;
                }
                const returnValue = hookParams[hookHandlerName]({
                    ctx,
                    ...helpers,
                    ...arg,
                });
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
                    Math.hypot(
                        pointer.x - initialPosition.x,
                        pointer.y - initialPosition.y,
                    ) >= ctx.tolerance
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
                    ctx.current.container ===
                    ctx.current.container.ownerDocument.scrollingElement;
                // If the container is the "ownerDocument.scrollingElement",
                // there is no need to get the scroll parent as it is the
                // scrollable element itself.
                // TODO: investigate if "getScrollParents" should not consider
                // the "ownerDocument.scrollingElement" directly.
                [ctx.current.scrollParentX, ctx.current.scrollParentY] =
                    isDocumentScrollingElement
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
                        // Limit the impact of width and height !important on the dragged element
                        "max-width": `${width}px`,
                        "max-height": `${height}px`,
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
                        if (
                            target &&
                            (params.allowDisconnected ||
                                ctx.current.element.isConnected)
                        ) {
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
                if (
                    scrollParentYEl ===
                    ctx.current.container.ownerDocument.scrollingElement
                ) {
                    yRect.y += scrollParentYEl.scrollTop;
                }

                const { direction, speed, threshold } = ctx.edgeScrolling;
                const correctedSpeed = (speed / 16) * deltaTime;

                /** @type {{ x?: [number, number], y?: [number, number] }} */
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
                    ctx.current.scrollParentY.scrollBy({
                        top: diffToScroll(diff.y),
                    });
                }
                if ((!direction || direction === "horizontal") && diff.x) {
                    ctx.current.scrollParentX.scrollBy({
                        left: diffToScroll(diff.x),
                    });
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

                const target = /** @type {HTMLElement} */ (ev.target);
                const initiationDelay =
                    ev.pointerType === "touch" ? ctx.touchDelay : ctx.delay;

                // A drag sequence can still be in progress if the pointerup occurred
                // outside of the window.
                dragEnd(null);

                const fullSelectorEl = /** @type {HTMLElement} */ (
                    target.closest(ctx.fullSelector)
                );
                if (
                    ev.button !== LEFT_CLICK ||
                    !ctx.enable() ||
                    !fullSelectorEl ||
                    (ctx.ignoreSelector && target.closest(ctx.ignoreSelector)) ||
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
                target.focus();
                let activeElement = document.activeElement;
                while (activeElement?.nodeName === "IFRAME") {
                    activeElement = /** @type {HTMLIFrameElement} */ (activeElement)
                        .contentDocument?.activeElement;
                }
                if (activeElement && !activeElement.contains(target)) {
                    /** @type {HTMLElement} */ (activeElement).blur();
                }

                const currentTarget = /** @type {HTMLElement} */ (ev.currentTarget);
                const { pointerId } = ev;
                ctx.current.initialPosition = { ...ctx.pointer };

                if (target.hasPointerCapture(pointerId)) {
                    target.releasePointerCapture(pointerId);
                }

                if (initiationDelay) {
                    if (hasTouch()) {
                        if (ev.pointerType === "touch") {
                            dom.addClass(
                                target.closest(ctx.elementSelector),
                                "o_touch_bounce",
                            );
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
                            for (const image of currentTarget.getElementsByTagName(
                                "img",
                            )) {
                                dom.setAttribute(image, "draggable", false);
                            }
                        }
                    }

                    ctx.current.timeout = browser.setTimeout(() => {
                        ctx.current.initialPosition = { ...ctx.pointer };

                        willStartDrag(target);

                        const { x: px, y: py } = ctx.pointer;
                        const { x, y, width, height } = dom.getRect(
                            ctx.current.element,
                        );
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
                } else if (
                    !params.allowDisconnected &&
                    !ctx.current.element.isConnected
                ) {
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
                dragEnd(/** @type {HTMLElement} */ (ev.target));
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
                current.containerRect = dom.getRect(container, {
                    adjust: true,
                });
                // If the scrolling element is within an iframe and the draggable
                // element is outside this iframe, the offsets must be computed taking
                // into account the iframe.
                let iframeOffsetX = 0;
                let iframeOffsetY = 0;
                const iframeEl = /** @type {HTMLIFrameElement} */ (
                    container.ownerDocument.defaultView.frameElement
                );
                if (iframeEl && !iframeEl.contentDocument?.contains(element)) {
                    const { x, y } = dom.getRect(/** @type {HTMLElement} */ (iframeEl));
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
                        current.scrollParentXRect = dom.getRect(scrollParentX, {
                            adjust: true,
                        });
                        current.scrollParentXRect.x += iframeOffsetX;
                        current.scrollParentXRect.y += iframeOffsetY;
                        const right = Math.min(
                            current.containerRect.left + container.scrollWidth,
                            current.scrollParentXRect.right,
                        );
                        current.containerRect.x = Math.max(
                            current.containerRect.x,
                            current.scrollParentXRect.x,
                        );
                        current.containerRect.width = right - current.containerRect.x;
                    }
                    if (scrollParentY) {
                        current.scrollParentYRect = dom.getRect(scrollParentY, {
                            adjust: true,
                        });
                        current.scrollParentYRect.x += iframeOffsetX;
                        current.scrollParentYRect.y += iframeOffsetY;
                        const bottom = Math.min(
                            current.containerRect.top + container.scrollHeight,
                            current.scrollParentYRect.bottom,
                        );
                        current.containerRect.y = Math.max(
                            current.containerRect.y,
                            current.scrollParentYRect.y,
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
            const state = setupHooks.wrapState({
                dragging: false,
                willDrag: false,
            });

            // Basic error handling asserting that the parameters are valid.
            for (const prop in allAcceptedParams) {
                const type = typeof params[prop];
                const acceptedTypes = allAcceptedParams[prop].map((t) =>
                    t.name.toLowerCase(),
                );
                if (params[prop]) {
                    if (!acceptedTypes.includes(type)) {
                        throw makeError(
                            `invalid type for property "${prop}" in parameters: expected { ${acceptedTypes.join(
                                ", ",
                            )} } and got ${type}`,
                        );
                    }
                } else if (MANDATORY_PARAMS.includes(prop) && !defaultParams[prop]) {
                    throw makeError(
                        `missing required property "${prop}" in parameters`,
                    );
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
                    /** @type {Record<string, any>} */
                    const params = Object.fromEntries(deps);
                    /** @type {Record<string, any>} */
                    const actualParams = {
                        ...defaultParams,
                        ...omit(params, "edgeScrolling"),
                    };
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
                            `no value found by "elements" selector: ${ctx.elementSelector}`,
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

                    callBuildHandler("onComputeParams", {
                        params: actualParams,
                    });

                    // Calls effect cleanup functions when preparing to re-render.
                    return effectCleanup.cleanup;
                },
                () => computeParams(params),
            );
            // Firefox currently (119.0.1) does not handle our pointer events
            // nicely when they happen from within the iframe. To work around
            // this, we use mouse events instead of pointer events.
            const useMouseEvents =
                isBrowserFirefox() && !hasTouch() && params.iframeWindow;
            // Effect depending on the `ref.el` to add triggering pointer events listener.
            setupHooks.setup(
                (el) => {
                    if (el) {
                        const { add, cleanup } = makeCleanupManager();
                        const { addListener } = makeDOMHelpers({
                            add,
                            cleanup,
                        });
                        const event = useMouseEvents ? "mousedown" : "pointerdown";
                        addListener(el, event, onPointerDown, {
                            noAddedStyle: true,
                        });
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
                () => [ctx.ref.el],
            );
            const addWindowListener = (type, listener, options) => {
                if (params.iframeWindow) {
                    setupHooks.addListener(
                        params.iframeWindow,
                        type,
                        listener,
                        options,
                    );
                }
                setupHooks.addListener(window, type, listener, options);
            };
            // Other global event listeners.
            const throttledOnPointerMove = setupHooks.throttle(onPointerMove);
            addWindowListener(
                useMouseEvents ? "mousemove" : "pointermove",
                throttledOnPointerMove,
                { passive: false },
            );
            addWindowListener(useMouseEvents ? "mouseup" : "pointerup", onPointerUp);
            addWindowListener("pointercancel", onPointerCancel);
            addWindowListener("keydown", onKeyDown, { capture: true });
            setupHooks.teardown(() => dragEnd(null));

            return state;
        },
    }[hookName];
}
