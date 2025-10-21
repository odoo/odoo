import { hasTouch, isBrowserFirefox, isIOS } from "@web/core/browser/feature_detection";
import { setRecurringAnimationFrame, throttleForAnimation } from "@web/core/utils/timing";
import { getParentFrame } from "@web/core/utils/ui";
import { closestScrollableX, closestScrollableY } from "../utils/scrolling";
import { AttributeManager, DraggableDebugManager } from "./draggable_utils";

/**
 * @typedef {{
 *  direction?: "horizontal" | "vertical" | "both";
 *  speed?: number;
 *  threshold?: number;
 * }} AutoScrollOptions
 *
 * @typedef {{
 *  cleanups: Map<HTMLElement | null, (() => any)[]>;
 *  container?: HTMLElement | null;
 *  element: HTMLElement;
 *  group?: HTMLElement;
 *  placeHolder?: HTMLElement;
 *  pointerX: number;
 *  pointerY: number;
 *  scrollParents?: [HTMLElement, HTMLElement];
 *  timeout: number;
 * }} DraggableCurrentSequence
 *
 * @typedef {{
 *  container: SimpleRect | null;
 *  element: SimpleRect;
 *  pointerId: number;
 *  pointerType: "mouse" | "pen" | "touch";
 *  pointerX: number;
 *  pointerY: number;
 * }} DraggableInitialContext
 *
 * @typedef {CustomEvent<unknown>} DraggableHookEvent
 *
 * @typedef {(event: DraggableHookEvent) => any} DraggableHookHandler
 *
 * @typedef {{
 *  canDrag: (this: Draggable, target: HTMLElement) => boolean;
 *  canDrop: (this: Draggable, target: HTMLElement) => boolean;
 *  onDrag: (this: Draggable, event: DraggableHookEvent) => any;
 *  onDragEnd: (this: Draggable, event: DraggableHookEvent) => any;
 *  onDragStart: (this: Draggable, event: DraggableHookEvent) => any;
 *  onDrop: (this: Draggable, event: DraggableHookEvent) => any;
 *  onSequenceEnd: (this: Draggable, event: DraggableHookEvent) => any;
 *  onSequenceStart: (this: Draggable, event: DraggableHookEvent) => any;
 * }} DraggableHooks
 *
 * @typedef {{
 *  destroy: (destroyDraggable: () => any) => any;
 *  update: (updateDraggable: () => any) => any;
 *  wrapState?: <T>(state: T) => T;
 * }} DraggableLifeCycleHooks
 *
 * @typedef {{
 *  dragging: boolean;
 * }} DraggableState
 *
 * @typedef {DraggableHooks & {
 *  autoScroll?: AutoScrollOptions;
 *  container?: string | ElementRef;
 *  cursor?: string;
 *  debug?: boolean;
 *  delay?: number;
 *  elements: string | Iterable<ElementRef>;
 *  followCursor?: boolean;
 *  groups?: string | Iterable<ElementRef>;
 *  handle?: string;
 *  optimistic?: boolean;
 *  placeHolder?: boolean;
 *  tolerance?: number;
 *  touchDelay?: number;
 * }} DraggableParameters
 *
 * @typedef {OwlRef | HTMLElement} ElementRef
 *
 * @typedef {{
 *  fromTop?: boolean;
 *  trimBorder?: boolean;
 *  trimPadding?: boolean;
 * }} GetRectOptions
 *
 * @typedef {ReturnType<import("@odoo/owl").useRef>} OwlRef
 *
 * @typedef {[x: number, y: number, width: number, height: number]} SimpleRect
 */

/**
 * @param {...keyof GLOBAL_EVENT_HANDLERS} eventTypes
 */
function addGlobalEvent(...eventTypes) {
    for (const eventType of eventTypes) {
        const [handler, options] = GLOBAL_EVENT_HANDLERS[eventType];
        for (const view of observedViews) {
            view.addEventListener(eventType, handler, options);
        }
    }
}

function findGlobalViews() {
    for (const view of observedViews) {
        for (const iframe of view.document.body.getElementsByTagName("iframe")) {
            observedViews.add(iframe.contentWindow);
        }
    }
}

/**
 * @param {HTMLElement | { view: Window; clientX: number; clientY: number }} eventOrElement
 */
function getTopCoordinates(eventOrElement) {
    /** @type {Window} */
    let view;
    /** @type {number} */
    let x;
    /** @type {number} */
    let y;
    if (eventOrElement.nodeType) {
        view = getView(eventOrElement);
        [x, y] = getRect(eventOrElement);
    } else {
        view = eventOrElement.view;
        x = eventOrElement.clientX;
        y = eventOrElement.clientY;
    }
    while (view !== view.parent) {
        const iframe = getParentFrame(view);
        if (iframe) {
            const rect = getRect(iframe, { trimBorder: true, trimPadding: true });
            x += rect[RECT_X];
            y += rect[RECT_Y];
        }
        view = view.parent;
    }
    return [x, y];
}

/**
 * @param {HTMLElement} target
 * @param {string | Iterable<ElementRef>} spec
 */
function getClosestElement(target, spec) {
    if (!spec) {
        return null;
    }
    if (typeof spec === "string") {
        return target.closest(spec);
    }
    for (const refOrEl of spec) {
        const el = getRefElement(refOrEl);
        if (el?.contains(target)) {
            return el;
        }
    }
    return null;
}

/**
 * @param {HTMLElement} element
 * @param {GetRectOptions} [options]
 * @returns {SimpleRect | null}
 */
function getRect(element, options) {
    if (!element) {
        return null;
    }
    const domRect = element.getBoundingClientRect();
    const rect = [domRect.x, domRect.y, domRect.width, domRect.height];
    let style;
    if (options?.fromTop) {
        [rect[RECT_X], rect[RECT_Y]] = getTopCoordinates({
            view: getView(element),
            clientX: rect[RECT_X],
            clientY: rect[RECT_Y],
        });
    }
    if (options?.trimBorder) {
        style = getComputedStyle(element);
        const bLeft = pixelValueToNumber(style.getPropertyValue("border-left"));
        const bRight = pixelValueToNumber(style.getPropertyValue("border-right"));
        const bTop = pixelValueToNumber(style.getPropertyValue("border-top"));
        const bBottom = pixelValueToNumber(style.getPropertyValue("border-bottom"));
        rect[RECT_X] += bLeft;
        rect[RECT_Y] += bTop;
        rect[RECT_W] -= bLeft + bRight;
        rect[RECT_H] -= bTop + bBottom;
    }
    if (options?.trimPadding) {
        style ||= getComputedStyle(element);
        const pLeft = pixelValueToNumber(style.getPropertyValue("padding-left"));
        const pRight = pixelValueToNumber(style.getPropertyValue("padding-right"));
        const pTop = pixelValueToNumber(style.getPropertyValue("padding-top"));
        const pBottom = pixelValueToNumber(style.getPropertyValue("padding-bottom"));
        rect[RECT_X] += pLeft;
        rect[RECT_Y] += pTop;
        rect[RECT_W] -= pLeft + pRight;
        rect[RECT_H] -= pTop + pBottom;
    }
    return rect;
}

/**
 * @param {ElementRef} refOrEl
 * @returns {HTMLElement | null}
 */
function getRefElement(refOrEl) {
    return (refOrEl?.nodeType === Node.ELEMENT_NODE ? refOrEl : refOrEl.el) || null;
}

/**
 * @param {HTMLElement} element
 */
function getView(element) {
    return element.ownerDocument.defaultView;
}

/**
 * @param {PointerEvent} ev
 */
function onClick(ev) {
    if (preventClick) {
        preventClick = false;
        safePrevent(ev, true);
    }
}

/**
 * @param {PointerEvent} ev
 */
function onContextMenu(ev) {
    if (activeInstance) {
        safePrevent(ev);
    }
}

/**
 * @param {MutationRecord[]} records
 */
function onGlobalMutation(records) {
    for (const record of records) {
        for (const node of record.addedNodes) {
            if (node.nodeName === "IFRAME" && node.contentWindow) {
                observedViews.add(node.contentWindow);
            }
        }
        for (const node of record.removedNodes) {
            if (node.nodeName === "IFRAME" && node.contentWindow) {
                observedViews.delete(node.contentWindow);
            }
        }
    }
}

/**
 * @param {KeyboardEvent} ev
 */
function onKeyDown(ev) {
    preventClick = false;
    if (activeInstance && !WHITE_LISTED_KEYS.includes(ev.key)) {
        safePrevent(ev, true);
        activeInstance._stopSequence(null, ev, `"keydown" [${ev.key}] event detected`);
    }
}

/**
 * @param {PointerEvent} ev
 */
function onPointerCancel(ev) {
    preventClick = false;
    if (activeInstance) {
        activeInstance._stopSequence(null, ev, `"pointercancel" [${ev.button}] event detected`);
    }
}

/**
 * @param {PointerEvent} ev
 */
function onPointerDown(ev) {
    preventClick = false;
    if (activeInstance) {
        activeInstance._stopSequence(null, ev, `"pointerdown" [${ev.button}] event detected`);
    }
    if (ev.button !== LEFT_CLICK) {
        return;
    }
    for (const instance of globalInstances) {
        const match = instance._findMatchingTarget(ev.target);
        if (match) {
            preventPointerDownEvent(ev, match.element);

            instance._startSequence(ev, match.element, match.container);
            break;
        }
    }
}

/**
 * @param {PointerEvent} ev
 */
function onPointerMove(ev) {
    if (activeInstance) {
        safePrevent(ev);
        activeInstance._drag(ev);
    }
}

/**
 * @param {PointerEvent} ev
 */
function onPointerUp(ev) {
    if (activeInstance) {
        activeInstance._drag(ev);
        activeInstance._stopSequence(ev.target, ev, `"pointerup" [${ev.button}] event detected`);
    }
}

function onTouchMove(ev) {
    safePrevent(ev);
}

function onTouchStart() {
    // Adds a non-passive listener on touchstart: this allows the subsequent "touchmove"
    // events to be cancelable and thus prevent parasitic "touchcancel" events to
    // be fired. Note that we DO NOT want to prevent touchstart events since they're
    // responsible of the native swipe scrolling.
}

/**
 * Converts a CSS pixel value to a number, removing the 'px' part.
 * @param {string} val
 * @returns {number}
 */
function pixelValueToNumber(val) {
    return parseFloat(val.endsWith("px") ? val.slice(0, -2) : val);
}

/**
 * In FireFox: elements with `overflow: hidden` will prevent "mouseenter"
 * and "mouseleave" events from firing on elements underneath them.
 *
 * This is the case when dragging a card by the heading. In such cases,
 * we can prevent the default action on the "pointerdown" event to allow
 * pointer events to fire properly.
 *
 * @see https://bugzilla.mozilla.org/show_bug.cgi?id=1352061
 * @see https://bugzilla.mozilla.org/show_bug.cgi?id=339293
 *
 * @param {PointerEvent} ev
 */
function preventPointerDownEvent(ev) {
    safePrevent(ev);

    const activeElement = ev.view.document.activeElement;
    if (activeElement && !activeElement.contains(ev.target)) {
        activeElement.blur();
    }

    ev.target.focus();

    if (ev.target.hasPointerCapture(ev.pointerId)) {
        ev.target.releasePointerCapture(ev.pointerId);
    }
}

/**
 * @param {unknown} value
 */
function px(value) {
    if (typeof value === "number") {
        value = Number(value.toFixed(3));
    }
    return String(value) + "px";
}

/**
 * @param {...keyof GLOBAL_EVENT_HANDLERS} eventTypes
 */
function removeGlobalEvent(...eventTypes) {
    for (const eventType of eventTypes) {
        const [handler, options] = GLOBAL_EVENT_HANDLERS[eventType];
        for (const view of observedViews) {
            view.removeEventListener(eventType, handler, options);
        }
    }
}

/**
 * @param {Event} ev
 * @param {boolean} [stop]
 */
function safePrevent(ev, stop) {
    if (ev.cancelable) {
        ev.preventDefault();
        if (stop) {
            ev.stopPropagation();
        }
    }
}

/**
 *
 * @param {Draggable | null} instance
 */
function setActiveInstance(instance) {
    if (activeInstance === instance) {
        return;
    }
    activeInstance = instance;
    if (activeInstance) {
        addGlobalEvent("keydown", "pointercancel", "pointermove", "pointerup");
        if (hasTouch()) {
            addGlobalEvent("contextmenu", "touchstart");
        }
    } else {
        removeGlobalEvent("keydown", "pointercancel", "pointermove", "pointerup");
        if (hasTouch()) {
            removeGlobalEvent("contextmenu", "touchmove", "touchstart");
        }
    }
    if (instance?.params.debug && !__debug__) {
        __debug__ = new DraggableDebugManager({ color: "red" });
        __debug__.attach(window.top.document.body);
    } else if (!instance?.params.debug && __debug__) {
        __debug__.detach();
        __debug__ = null;
    }
}

function startObservingDragSequences() {
    findGlobalViews();
    addGlobalEvent("click", "pointerdown");
    globalObserver = new MutationObserver(onGlobalMutation);
    for (const view of observedViews) {
        if (view.document?.body) {
            globalObserver.observe(view.document?.body, {
                childList: true,
                subtree: true,
            });
        }
    }
}

function stopObservingDragSequences() {
    removeGlobalEvent("click", "pointerdown");
    if (globalObserver) {
        globalObserver.disconnect();
        globalObserver = null;
    }
}

const CLASS_NAME_PREFIX = "o-draggable";
const CLASS_NAMES = {
    dragged: `${CLASS_NAME_PREFIX}-dragged`,
    noFollow: `${CLASS_NAME_PREFIX}-no-follow`,
    optimistic: `${CLASS_NAME_PREFIX}-optimistic`,
    placeHolder: `${CLASS_NAME_PREFIX}-placeholder`,
};
/** @type {DraggableParameters} */
const DEFAULT_PARAMETERS = {
    autoScroll: {
        speed: 10,
        threshold: 30,
    },
    elements: `[draggable]`,
    followCursor: true,
    delay: 0,
    tolerance: 10,
    touchDelay: 300,
};
const GLOBAL_EVENT_HANDLERS = {
    click: [onClick],
    contextmenu: [onContextMenu],
    keydown: [onKeyDown],
    pointercancel: [onPointerCancel],
    pointerdown: [onPointerDown],
    pointermove: [throttleForAnimation(onPointerMove)],
    pointerup: [onPointerUp],
    touchmove: [onTouchMove, { passive: false }],
    touchstart: [onTouchStart, { passive: false }],
};
const LEFT_CLICK = 0;
const RE_BANG = /\s*!\s*/;
const RECT_X = 0;
const RECT_Y = 1;
const RECT_W = 2;
const RECT_H = 3;
const STYLE_PREFIX = "--_draggable";
const STYLE_VARIABLES = {
    x: `${STYLE_PREFIX}-x`,
    y: `${STYLE_PREFIX}-y`,
    minX: `${STYLE_PREFIX}-min-x`,
    minY: `${STYLE_PREFIX}-min-y`,
    maxX: `${STYLE_PREFIX}-max-x`,
    maxY: `${STYLE_PREFIX}-max-y`,
    width: `${STYLE_PREFIX}-width`,
    height: `${STYLE_PREFIX}-height`,
    offsetX: `${STYLE_PREFIX}-offset-x`,
    offsetY: `${STYLE_PREFIX}-offset-y`,
};
const WHITE_LISTED_KEYS = ["Alt", "AltGraph", "CapsLock", "Control", "Meta", "Shift", "Tab"];

const globalAttributeManager = new AttributeManager();
/** @type {Set<Draggable>} */
const globalInstances = new Set();
/** @type {Set<Window>} */
const observedViews = new Set([window.top]);
/**
 * Draggable instance with an *active* drag sequence.
 * @type {Draggable | null}
 */
let activeInstance = null;
/** @type {MutationObserver | null} */
let globalObserver = null;
let preventClick = false;
/** @type {DraggableDebugManager | null} */
let __debug__ = null;

export class Draggable {
    /**
     * @param {DraggableParameters} [params]
     * @param {DraggableLifeCycleHooks} [lifeCycleHooks]
     */
    constructor(params, lifeCycleHooks) {
        params ||= {};

        /**
         * @private
         * @type {DraggableCurrentSequence | null}
         */
        this.current = null;
        /**
         * @private
         * @type {DraggableInitialContext | null}
         */
        this.init = null;
        /**
         * @private
         * @type {DraggableParameters}
         */
        this.params = Object.create(params);
        const paramsDescriptors = Object.getOwnPropertyDescriptors(params);
        for (const property in DEFAULT_PARAMETERS) {
            const descriptor = paramsDescriptors[property];
            if (
                !descriptor ||
                ("value" in descriptor &&
                    (descriptor.value === null || descriptor.value === undefined))
            ) {
                this.params[property] = DEFAULT_PARAMETERS[property];
            }
        }
        /** @type {DraggableState} */
        this.state = {
            dragging: false,
        };
        if (lifeCycleHooks) {
            if (lifeCycleHooks.wrapState) {
                this.state = lifeCycleHooks.wrapState?.(this.state);
            }
            lifeCycleHooks.update(this._update.bind(this));
            lifeCycleHooks.destroy(this._destroy.bind(this));
        }

        /** @type {typeof this._callHook} */
        this._callOnDrag = throttleForAnimation(this._callHook.bind(this, "onDrag"));
    }

    //-------------------------------------------------------------------------
    // Public
    //-------------------------------------------------------------------------

    cleanupOptimisticMoves() {
        this._stopSequence(null, null, `optimistic moves cleaned up`);
    }

    //-------------------------------------------------------------------------
    // Private
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {HTMLElement | null} element
     * @param {() => any} cleanupFn
     */
    _addCleanup(element, cleanupFn) {
        if (!this.current) {
            return;
        }
        if (!this.current.cleanups.has(element)) {
            this.current.cleanups.set(element, []);
        }
        const cleanups = this.current.cleanups.get(element);
        if (typeof cleanupFn === "function") {
            cleanups.push(cleanupFn);
        }
    }

    /**
     * @private
     * @param {HTMLElement} element
     */
    _attachPlaceHolder(element) {
        const placeHolder = element.cloneNode(true);
        placeHolder.classList.add(CLASS_NAMES.placeHolder);

        element.after(placeHolder);
        this._addCleanup(placeHolder, this._detachPlaceHolder.bind(this, placeHolder));

        return placeHolder;
    }

    /**
     * Applies scroll to the container if the current element is near the edge of
     * the container.
     *
     * @private
     * @param {number} deltaTime
     */
    _autoScroll(deltaTime) {
        const {
            container,
            element,
            pointerX,
            pointerY,
            scrollParents: [scrollParentX, scrollParentY],
        } = this.current;
        const {
            autoScroll: { direction, speed, threshold },
        } = this.params;
        const dir = direction || "both";
        const elRect = getRect(element, { fromTop: true });
        const xRect = getRect(scrollParentX, { fromTop: true });
        const yRect = getRect(scrollParentY, { fromTop: true });

        // "getBoundingClientRect()"" (used in "getRect()") gives the
        // distance from the element's top to the viewport, excluding
        // scroll position. Only the "document.scrollingElement" element
        // ("<html>") accounts for scrollTop.
        if (scrollParentY === container?.ownerDocument.scrollingElement) {
            yRect[RECT_Y] += scrollParentY.scrollTop;
        }

        const correctedSpeed = (speed / 16) * deltaTime;
        const diff = {};
        if (xRect) {
            const maxWidth = xRect[RECT_X] + xRect[RECT_W];
            const xMin = Math.min(pointerX, elRect[RECT_X]);
            const xMax = Math.max(pointerX, elRect[RECT_X] + elRect[RECT_W]);
            if (xMin <= xRect[RECT_X] + threshold) {
                diff.x = [xMin - xRect[RECT_X], -1];
            } else if (xMax >= maxWidth - threshold) {
                diff.x = [maxWidth - xMax, 1];
            }
        }
        if (yRect) {
            const maxHeight = yRect[RECT_Y] + yRect[RECT_H];
            const yMin = Math.min(pointerY, elRect[RECT_Y]);
            const yMax = Math.max(pointerY, elRect[RECT_Y] + elRect[RECT_H]);
            if (yMin <= yRect[RECT_Y] + threshold) {
                diff.y = [yMin - yRect[RECT_Y], -1];
            } else if (yMax >= maxHeight - threshold) {
                diff.y = [maxHeight - yMax, 1];
            }
        }

        if ((dir === "both" || dir === "horizontal") && diff.x) {
            const [delta, sign] = diff.x;
            if (
                (sign < 0 && scrollParentX.scrollLeft > 0) ||
                (sign > 0 && scrollParentX.scrollLeft + xRect[RECT_W] < scrollParentX.scrollWidth)
            ) {
                scrollParentX.addEventListener("scroll", this._onScroll.bind(this), {
                    once: true,
                });
                scrollParentX.scrollBy({
                    left: (1 - Math.max(delta, 0) / threshold) * correctedSpeed * sign,
                });
            }
        }
        if ((dir === "both" || dir === "vertical") && diff.y) {
            const [delta, sign] = diff.y;
            if (
                (sign < 0 && scrollParentY.scrollTop > 0) ||
                (sign > 0 && scrollParentY.scrollTop + yRect[RECT_H] < scrollParentY.scrollHeight)
            ) {
                scrollParentY.addEventListener("scroll", this._onScroll.bind(this), {
                    once: true,
                });
                scrollParentY.scrollBy({
                    top: (1 - Math.max(delta, 0) / threshold) * correctedSpeed * sign,
                });
            }
        }
    }

    /**
     * @private
     * @param {keyof DraggableHooks} name
     * @param {unknown} payload
     */
    _callHook(name, payload) {
        const hook = this.params[name];
        let result = null;
        if (typeof hook === "function") {
            result = hook.call(this, payload);
        }
        __debug__?.log(this, name, payload, result);
        return result;
    }

    /**
     * @private
     * @param {HTMLElement} target
     */
    _canDrop(target) {
        if (!target) {
            // No target on which to drop the current element
            return false;
        }

        if (!this.current?.element.isConnected) {
            // Dragged target is not in the DOM anymore
            return false;
        }

        // Let the owner decide if the given target is "droppable"
        return this._callHook("canDrop", { target }) ?? true;
    }

    /**
     * @private
     */
    _destroy() {
        if (!globalInstances.has(this)) {
            return;
        }
        this._stopSequence(null, null, `draggable instance destroyed`);
        globalInstances.delete(this);
        if (!globalInstances.size) {
            stopObservingDragSequences();
        }
    }

    /**
     * @private
     * @param {HTMLElement} placeHolder
     */
    _detachPlaceHolder(placeHolder) {
        placeHolder.remove();
    }

    /**
     * @private
     * @param {PointerEvent} ev
     */
    _drag(ev) {
        if (this.current) {
            [this.current.pointerX, this.current.pointerY] = getTopCoordinates(ev);
            __debug__?.drawPath(this.current.pointerX, this.current.pointerY);

            if (this.current.timeout) {
                if (this._hasMovedPassedTolerance()) {
                    this._stopSequence(null, ev, `pointer moved too far`);
                }
                return;
            }
        }
        if (!this.state.dragging && this.current?.element && this._hasMovedPassedTolerance()) {
            this._startDragging(ev);
        }
        if (this.state.dragging) {
            if (this.params.followCursor) {
                this._moveToPointer(this.current.element);
            }
            this._callOnDrag({ event: ev });
        }
    }

    /**
     * @private
     * @param {HTMLElement} target
     */
    _findMatchingTarget(target) {
        const { container, elements, handle } = this.params;

        // 1. Check that target is within (or is) a matching element
        const matchingElement = getClosestElement(target, elements || DEFAULT_PARAMETERS.elements);
        if (!matchingElement) {
            return false;
        }

        // 2. Check that the target is within the handle (if any)
        if (handle && !target.closest(handle)) {
            return false;
        }

        // 3. Check that matching element is within container (if any)
        let containerElement = null;
        if (container) {
            containerElement =
                typeof container === "string"
                    ? target.ownerDocument.querySelector(container)
                    : getRefElement(container);
            if (!containerElement?.contains(matchingElement)) {
                return false;
            }
        }

        // 4. Call "canDrag" to check with owner if sequence can start
        const canDrag =
            this._callHook("canDrag", {
                target: matchingElement,
            }) ?? true;
        if (!canDrag) {
            return false;
        }

        return {
            container: containerElement,
            element: matchingElement,
        };
    }

    _getDelay() {
        return this.init.pointerType !== "mouse"
            ? this.params.touchDelay || this.params.delay
            : this.params.delay;
    }

    /**
     * @private
     */
    _hasMovedPassedTolerance() {
        const { tolerance } = this.params;
        if (!tolerance) {
            return true;
        }
        const draggedDistance = Math.hypot(
            this.current.pointerX - this.init.pointerX,
            this.current.pointerY - this.init.pointerY
        );
        return draggedDistance >= tolerance;
    }

    /**
     * @param {HTMLElement} element
     */
    _moveToPointer(element) {
        const styleEntries = [
            [STYLE_VARIABLES.x, px(this.current.pointerX)],
            [STYLE_VARIABLES.y, px(this.current.pointerY)],
        ];
        if (this.current.container) {
            const [x, y, width, height] = this.init.container;
            const view = element.ownerDocument.defaultView;
            styleEntries.push(
                [STYLE_VARIABLES.minX, px(Math.max(x, 0))],
                [STYLE_VARIABLES.maxX, px(Math.min(x + width, view.innerWidth))],
                [STYLE_VARIABLES.minY, px(Math.max(y, 0))],
                [STYLE_VARIABLES.maxY, px(Math.min(y + height, view.innerHeight))]
            );
        }
        this._setStyle(element, styleEntries);
    }

    /**
     * @param {Event} ev
     */
    _onScroll(ev) {
        if (this.state.dragging) {
            if (this.params.followCursor) {
                this._moveToPointer(this.current.element);
            }
            this._callOnDrag({ event: ev });
        }
    }

    /**
     * @param {HTMLElement} element
     */
    _saveAttributes(element) {
        this._addCleanup(element, globalAttributeManager.save(element));
    }

    /**
     * @param {HTMLElement} element
     * @param {Iterable<[string, string | number]>} styleEntries
     */
    _setStyle(element, styleEntries) {
        this._saveAttributes(element);
        for (const [property, valueAndPriority] of styleEntries) {
            const [value, priority] = String(valueAndPriority).split(RE_BANG);
            element.style.setProperty(property, value, priority);
        }
    }

    /**
     * @param {PointerEvent} ev
     */
    _startDragging(ev) {
        this.state.dragging = true;
        preventClick = true;

        __debug__?.setColor("green");

        if (this.current.timeout) {
            clearTimeout(this.current.timeout);
        }
        this.current.timeout = null;

        const { element } = this.current;
        const { autoScroll, followCursor, groups, placeHolder } = this.params;
        this.current.scrollParents = [
            closestScrollableX(element, { crossFrames: true }),
            closestScrollableY(element, { crossFrames: true }),
        ];
        if (groups) {
            this.current.group = getClosestElement(element, groups);
        }
        this._saveAttributes(element);
        if (followCursor) {
            if (placeHolder) {
                this.current.placeHolder = this._attachPlaceHolder(element);
            }
            element.classList.add(CLASS_NAMES.dragged);
            const [x, y, width, height] = this.init.element;
            this._setStyle(element, [
                [STYLE_VARIABLES.width, px(width)],
                [STYLE_VARIABLES.height, px(height)],
                [STYLE_VARIABLES.offsetX, px(this.init.pointerX - x)],
                [STYLE_VARIABLES.offsetY, px(this.init.pointerY - y)],
            ]);
            this._moveToPointer(element);

            if (__debug__) {
                const elRect = this.init.element;
                const [ex, ey] = getTopCoordinates({
                    view: getView(element),
                    clientX: elRect[RECT_X],
                    clientY: elRect[RECT_Y],
                });
                __debug__?.drawRect(ex, ey, elRect[RECT_W], elRect[RECT_H], {
                    label: true,
                    color: "purple",
                });
                if (this.current.container) {
                    const cRect = this.init.container;
                    const [cx, cy] = getTopCoordinates({
                        view: getView(this.current.container),
                        clientX: cRect[RECT_X],
                        clientY: cRect[RECT_Y],
                    });
                    __debug__?.drawRect(cx, cy, cRect[RECT_W], cRect[RECT_H], {
                        label: true,
                        color: "red",
                    });
                }
                if (this.params.autoScroll) {
                    const { threshold } = this.params.autoScroll;
                    const [scrollParentX, scrollParentY] = this.current.scrollParents;
                    if (scrollParentX && scrollParentX === scrollParentY) {
                        const spRect = getRect(scrollParentX);
                        const [spX, spY] = getTopCoordinates(scrollParentX);
                        __debug__?.drawRect(
                            spX + threshold,
                            spY + threshold,
                            spRect[RECT_W] - threshold * 2,
                            spRect[RECT_H] - threshold * 2,
                            {
                                label: "Scroll parent X & Y",
                                color: "blue",
                            }
                        );
                    } else {
                        if (scrollParentX) {
                            const spRect = getRect(scrollParentX);
                            const [spX, spY] = getTopCoordinates(scrollParentX);
                            __debug__?.drawRect(
                                spX + threshold,
                                spY,
                                spRect[RECT_W] - threshold * 2,
                                spRect[RECT_H],
                                {
                                    label: "Scroll parent X",
                                    color: "blue",
                                }
                            );
                        }
                        if (scrollParentY) {
                            const spRect = getRect(scrollParentY);
                            const [spX, spY] = getTopCoordinates(scrollParentY);
                            __debug__?.drawRect(
                                spX,
                                spY + threshold,
                                spRect[RECT_W],
                                spRect[RECT_H] - threshold * 2,
                                {
                                    label: "Scroll parent Y",
                                    color: "cyan",
                                }
                            );
                        }
                    }
                }
            }
        } else {
            element.classList.add(CLASS_NAMES.noFollow);
        }

        element.setPointerCapture(this.init.pointerId);
        if (hasTouch()) {
            addGlobalEvent("touchmove");
        }

        if (autoScroll && (this.current.scrollParents[0] || this.current.scrollParents[1])) {
            const stopAutoScroll = setRecurringAnimationFrame(this._autoScroll.bind(this));
            this._addCleanup(null, stopAutoScroll);
        }

        if (this.params.cursor) {
            const { body } = element.ownerDocument;
            this._setStyle(body, [["cursor", `${this.params.cursor} !important`]]);
        }

        this._callHook("onDragStart", { event: ev });
    }

    /**
     * @param {PointerEvent} ev
     * @param {HTMLElement} element
     * @param {HTMLElement | null} [container]
     */
    _startSequence(ev, element, container) {
        setActiveInstance(this);

        const [x, y] = getTopCoordinates(ev);
        this.init = {
            container: getRect(container, { trimPadding: true }),
            element: getRect(element),
            pointerId: ev.pointerId,
            pointerType: ev.pointerType,
            pointerX: x,
            pointerY: y,
        };
        this.current = {
            cleanups: new Map(),
            container,
            element,
            group: null,
            pointerX: x,
            pointerY: y,
            scrollParents: [],
            timeout: null,
        };
        if (this.params.groups) {
            this.current.group = getClosestElement(element, this.params.groups);
        }
        const delay = this._getDelay();
        if (delay) {
            __debug__?.drawLoadingCircle(
                this.current.pointerX,
                this.current.pointerY,
                this.params.tolerance || 10,
                delay
            );
            if (isBrowserFirefox()) {
                // On Firefox mobile, long-touch events trigger an unpreventable
                // context menu to appear. To prevent this, all linkes are removed
                // from the dragged elements during the drag sequence.
                const links = [...element.querySelectorAll("[href]")];
                if (element.hasAttribute("href")) {
                    links.unshift(element);
                }
                for (const link of links) {
                    this._saveAttributes(link);
                    link.removeAttribute("href");
                }
            }
            if (isIOS()) {
                // On Safari mobile, any image can be dragged regardless
                // of the 'user-select' property.
                for (const image of element.getElementsByTagName("img")) {
                    this._saveAttributes(image);
                    image.setAttribute("draggable", "false");
                }
            }
            this.current.timeout = setTimeout(this._startDragging.bind(this, ev), delay);
        } else {
            __debug__?.drawCircle(
                this.current.pointerX,
                this.current.pointerY,
                this.params.tolerance || 10
            );
        }

        this._callHook("onSequenceStart", { event: ev });
    }

    /**
     * @private
     * @param {HTMLElement} target
     * @param {Event} [event]
     * @param {string} [reason]
     */
    _stopDragging(target, event, reason) {
        if (this._canDrop(target)) {
            this._callHook("onDrop", {
                event,
                target,
            });
        }
        this._callHook("onDragEnd", {
            event,
            reason: reason || "unknown reason",
            target,
        });
        this.state.dragging = false;
        this.current.element.releasePointerCapture(this.init.pointerId);
    }

    /**
     * @private
     * @param {HTMLElement | null} target
     * @param {Event | null} [event]
     * @param {string} [reason]
     */
    _stopSequence(target, event, reason) {
        GLOBAL_EVENT_HANDLERS.pointermove[0].cancel();
        this._callOnDrag.cancel();

        if (this.current?.timeout) {
            clearTimeout(this.current.timeout);
        }
        const keepOptimisticMove = this.params.optimistic && this.state.dragging && target;

        if (this.state.dragging) {
            this._stopDragging(target, event, reason);
        }

        if (this.current) {
            const { cleanups, element } = this.current;
            /** @type {(() => any)[] | undefined} */
            let optimisticCleanups;
            if (keepOptimisticMove) {
                optimisticCleanups = cleanups.get(element);
                cleanups.delete(element);
            }
            for (const [element, elCleanups] of cleanups) {
                for (const cleanup of elCleanups) {
                    cleanup(element);
                }
            }
            cleanups.clear();
            if (keepOptimisticMove) {
                element.classList.remove(CLASS_NAMES.dragged);
                element.classList.add(CLASS_NAMES.optimistic);
                cleanups.set(element, optimisticCleanups);
            } else {
                this.current = null;
                this.init = null;
            }
        }

        if (this === activeInstance) {
            this._callHook("onSequenceEnd", { event });
        }

        setActiveInstance(null);
    }

    _update() {
        if (globalInstances.has(this)) {
            return;
        }
        if (!globalInstances.size) {
            startObservingDragSequences();
        }
        globalInstances.add(this);

        this._stopSequence(null, null, `lifecycle update`);
    }
}
