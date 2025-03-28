/** @odoo-module */

import { HootDomError, getTag, isFirefox, isIterable } from "../hoot_dom_utils";
import {
    getActiveElement,
    getDocument,
    getNextFocusableElement,
    getNodeRect,
    getNodeValue,
    getParentFrame,
    getPreviousFocusableElement,
    getStyle,
    getWindow,
    isCheckable,
    isEditable,
    isEventTarget,
    isNode,
    isNodeFocusable,
    parseDimensions,
    parsePosition,
    queryAll,
    queryFirst,
    setDimensions,
    toSelector,
} from "./dom";
import { microTick } from "./time";

/**
 * @typedef {Target | Promise<Target>} AsyncTarget
 *
 * @typedef {"auto" | "blur" | "enter" | "tab" | false} ConfirmAction
 *
 * @typedef {{
 *  cancel: (options?: EventOptions) => Promise<EventList>;
 *  drop: (to?: AsyncTarget, options?: PointerOptions) => Promise<EventList>;
 *  moveTo: (to?: AsyncTarget, options?: PointerOptions) => Promise<DragHelpers>;
 * }} DragHelpers
 *
 * @typedef {import("./dom").Position} Position
 *
 * @typedef {import("./dom").Dimensions} Dimensions
 *
 * @typedef {((ev: Event) => boolean) | EventType} EventListPredicate
 *
 * @typedef {{
 *  eventInit?: EventInit;
 * }} EventOptions generic event options
 *
 * @typedef {{
 *  clientX: number;
 *  clientY: number;
 *  pageX: number;
 *  pageY: number;
 *  screenX: number;
 *  screenY: number;
 * }} EventPosition
 *
 * @typedef {keyof HTMLElementEventMap | keyof WindowEventMap} EventType
 *
 * @typedef {EventOptions & {
 *  confirm?: ConfirmAction;
 *  composition?: boolean;
 *  instantly?: boolean;
 * }} FillOptions
 *
 * @typedef {string | number | MaybeIterable<File>} InputValue
 *
 * @typedef {EventOptions & KeyboardEventInit} KeyboardOptions
 *
 * @typedef {string | string[]} KeyStrokes
 *
 * @typedef {EventOptions & QueryOptions & {
 *  button?: number,
 *  position?: Side | `${Side}-${Side}` | Position;
 *  relative?: boolean;
 * }} PointerOptions
 *
 * @typedef {import("./dom").QueryOptions} QueryOptions
 *
 * @typedef {EventOptions & QueryOptions & {
 *  force?: boolean;
 *  initiator?: "keyboard" | "scrollbar" | "wheel" | null;
 *  relative?: boolean;
 * }} ScrollOptions
 *
 * @typedef {EventOptions & {
 *  target: AsyncTarget;
 * }} SelectOptions
 *
 * @typedef {"bottom" | "left" | "right" | "top"} Side
 */

/**
 * @template [T=EventInit]
 * @typedef {T & {
 *  target: EventTarget;
 *  type: EventType;
 * }} FullEventInit
 */

/**
 * @template T
 * @typedef {T | Iterable<T>} MaybeIterable
 */

/**
 * @template [T=Node]
 * @typedef {import("./dom").Target<T>} Target
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    AnimationEvent,
    ClipboardEvent,
    CompositionEvent,
    console: { dir: $dir, groupCollapsed: $groupCollapsed, groupEnd: $groupEnd, log: $log },
    DataTransfer,
    document,
    DragEvent,
    ErrorEvent,
    Event,
    FocusEvent,
    KeyboardEvent,
    Math: { ceil: $ceil, max: $max, min: $min },
    MouseEvent,
    Number: { isInteger: $isInteger, isNaN: $isNaN, parseFloat: $parseFloat },
    Object: { assign: $assign, create: $create, values: $values },
    PointerEvent,
    PromiseRejectionEvent,
    String,
    SubmitEvent,
    Touch,
    TouchEvent,
    TypeError,
    WheelEvent,
} = globalThis;
/** @type {Document["createRange"]} */
const $createRange = document.createRange.bind(document);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {Event} ev
 */
const cancelTrustedEvent = (ev) => {
    if (ev.isTrusted && runTime.eventsToIgnore.includes(ev.type)) {
        runTime.eventsToIgnore.splice(runTime.eventsToIgnore.indexOf(ev.type), 1);
        ev.stopPropagation();
        ev.stopImmediatePropagation();
        ev.preventDefault();
    }
};

/**
 * @param {HTMLElement} target
 * @param {number} start
 * @param {number} end
 */
const changeSelection = async (target, start, end) => {
    if (!isNil(start) && !isNil(target.selectionStart)) {
        target.selectionStart = start;
    }
    if (!isNil(end) && !isNil(target.selectionEnd)) {
        target.selectionEnd = end;
    }
};

/**
 * @param {HTMLElement} target
 * @param {number} x
 */
const constrainScrollX = (target, x) => {
    let { offsetWidth, scrollWidth } = target;
    const document = getDocument(target);
    if (target === document || target === document.documentElement) {
        // <html> elements in iframes consider the width of the <iframe> element
        const iframe = getParentFrame(target);
        if (iframe) {
            ({ offsetWidth } = iframe);
        }
    }
    const maxScrollLeft = scrollWidth - offsetWidth;
    const { direction } = getStyle(target);
    const [min, max] = direction === "rtl" ? [-maxScrollLeft, 0] : [0, maxScrollLeft];
    return $min($max(x, min), max);
};

/**
 * @param {HTMLElement} target
 * @param {number} y
 */
const constrainScrollY = (target, y) => {
    let { offsetHeight, scrollHeight } = target;
    const document = getDocument(target);
    if (target === document || target === document.documentElement) {
        // <html> elements in iframes consider the height of the <iframe> element
        const iframe = getParentFrame(target);
        if (iframe) {
            ({ offsetHeight } = iframe);
        }
    }
    return $min($max(y, 0), scrollHeight - offsetHeight);
};

/**
 * @param {HTMLInputElement | HTMLTextAreaElement} target
 */
const deleteSelection = (target) => {
    const { selectionStart, selectionEnd, value } = target;
    return value.slice(0, selectionStart) + value.slice(selectionEnd);
};

/**
 * @template {EventTarget} T
 * @param {{
 *  target: T;
 *  events: EventType[];
 *  additionalEvents?: EventType[];
 *  callback?: (target: T) => any;
 *  options?: EventInit;
 * }} params
 */
const dispatchAndIgnore = async ({ target, events, additionalEvents = [], callback, options }) => {
    for (const eventType of [...events, ...additionalEvents]) {
        runTime.eventsToIgnore.push(eventType);
    }
    if (callback) {
        callback(target);
    }
    for (const eventType of events) {
        await dispatch(target, eventType, options);
    }
};

/**
 *
 * @param {EventTarget} target
 * @param {EventType} eventType
 * @param {PointerEventInit} eventInit
 * @param {{
 *  mouse?: [EventType, MouseEventInit];
 *  touch?: [EventType, TouchEventInit];
 * }} additionalEvents
 */
const dispatchPointerEvent = async (target, eventType, eventInit, { mouse, touch }) => {
    const pointerEvent = await dispatch(target, eventType, eventInit);
    let prevented = isPrevented(pointerEvent);
    if (hasTouch()) {
        if (touch && runTime.pointerDownTarget) {
            const [touchEventType, touchEventInit] = touch;
            await dispatch(runTime.pointerDownTarget, touchEventType, touchEventInit || eventInit);
        }
    } else {
        if (mouse && !prevented) {
            const [mouseEventType, mouseEventInit] = mouse;
            const mouseEvent = await dispatch(target, mouseEventType, mouseEventInit || eventInit);
            prevented = isPrevented(mouseEvent);
        }
    }
    return prevented;
};

/**
 * @param {Iterable<Event>} events
 * @param {EventType} eventType
 * @param {EventInit} eventInit
 */
const dispatchRelatedEvents = async (events, eventType, eventInit) => {
    for (const event of events) {
        if (!event.target || isPrevented(event)) {
            break;
        }
        await dispatch(event.target, eventType, eventInit);
    }
};

/**
 * @template T
 * @param {MaybeIterable<T>} value
 * @returns {T[]}
 */
const ensureArray = (value) => (isIterable(value) ? [...value] : [value]);

const getCurrentEvents = () => {
    const eventType = currentEventTypes.at(-1);
    if (!eventType) {
        return [];
    }
    currentEvents[eventType] ||= [];
    return currentEvents[eventType];
};

const getDefaultRunTimeValue = () => ({
    // Composition
    isComposing: false,

    // Drag & drop
    canStartDrag: false,
    isDragging: false,
    lastDragOverCancelled: false,

    // Pointer
    clickCount: 0,
    key: null,
    pointerDownTarget: null,
    pointerDownTimeout: 0,
    pointerTarget: null,
    /** @type {EventPosition | {}} */
    position: {},
    previousPointerDownTarget: null,
    previousPointerTarget: null,
    /** @type {EventPosition | {}} */
    touchStartPosition: {},

    // File
    fileInput: null,

    // Buttons
    buttons: 0,

    // Modifier keys
    modifierKeys: {},

    /**
     * Ignored events ("select" by default since it is sometimes dispatched by
     * focusing an input).
     * @type {EventType[]}
     */
    eventsToIgnore: [],
});

/**
 * Returns the list of nodes containing n2 (included) that do not contain n1.
 *
 * @param {Element} [el1]
 * @param {Element} [el2]
 */
const getDifferentParents = (el1, el2) => {
    if (!el1 && !el2) {
        // No given elements => no parents
        return [];
    } else if (!el1 && el2) {
        // No first element => only parents of second element
        [el1, el2] = [el2, el1];
    }
    const parents = [el2 || el1];
    while (parents[0].parentElement) {
        const parent = parents[0].parentElement;
        if (el2 && parent.contains(el1)) {
            break;
        }
        parents.unshift(parent);
    }
    return parents;
};

/**
 * @template {typeof Event} T
 * @param {EventType} eventType
 * @returns {[T, ((attrs: FullEventInit) => EventInit), number]}
 */
const getEventConstructor = (eventType) => {
    switch (eventType) {
        // Mouse events
        case "dblclick":
        case "mousedown":
        case "mouseup":
        case "mousemove":
        case "mouseover":
        case "mouseout":
            return [MouseEvent, mapMouseEvent, BUBBLES | CANCELABLE | VIEW];
        case "mouseenter":
        case "mouseleave":
            return [MouseEvent, mapMouseEvent, VIEW];

        // Pointer events
        case "auxclick":
        case "click":
        case "contextmenu":
        case "pointerdown":
        case "pointerup":
        case "pointermove":
        case "pointerover":
        case "pointerout":
            return [PointerEvent, mapPointerEvent, BUBBLES | CANCELABLE | VIEW];
        case "pointerenter":
        case "pointerleave":
        case "pointercancel":
            return [PointerEvent, mapPointerEvent, VIEW];

        // Focus events
        case "blur":
        case "focus":
            return [FocusEvent, mapEvent];
        case "focusin":
        case "focusout":
            return [FocusEvent, mapEvent, BUBBLES];

        // Clipboard events
        case "cut":
        case "copy":
        case "paste":
            return [ClipboardEvent, mapEvent, BUBBLES];

        // Keyboard events
        case "keydown":
        case "keyup":
            return [KeyboardEvent, mapKeyboardEvent, BUBBLES | CANCELABLE | VIEW];

        // Drag events
        case "drag":
        case "dragend":
        case "dragenter":
        case "dragstart":
        case "dragleave":
        case "dragover":
        case "drop":
            return [DragEvent, mapEvent, BUBBLES];

        // Input events
        case "beforeinput":
            return [InputEvent, mapInputEvent, BUBBLES | CANCELABLE | VIEW];
        case "input":
            return [InputEvent, mapInputEvent, BUBBLES | VIEW];

        // Composition events
        case "compositionstart":
        case "compositionend":
            return [CompositionEvent, mapEvent, BUBBLES];

        // Selection events
        case "select":
        case "selectionchange":
            return [Event, mapEvent, BUBBLES];

        // Touch events
        case "touchstart":
        case "touchend":
        case "touchmove":
            return [TouchEvent, mapTouchEvent, BUBBLES | CANCELABLE | VIEW];
        case "touchcancel":
            return [TouchEvent, mapTouchEvent, BUBBLES | VIEW];

        // Resize events
        case "resize":
            return [Event, mapEvent];

        // Submit events
        case "submit":
            return [SubmitEvent, mapEvent, BUBBLES | CANCELABLE];

        // Wheel events
        case "wheel":
            return [WheelEvent, mapWheelEvent, BUBBLES | VIEW];

        // Animation events
        case "animationcancel":
        case "animationend":
        case "animationiteration":
        case "animationstart": {
            return [AnimationEvent, mapEvent, BUBBLES | CANCELABLE];
        }

        // Error events
        case "error":
            return [ErrorEvent, mapEvent];
        case "unhandledrejection":
            return [PromiseRejectionEvent, mapEvent, CANCELABLE];

        // Unload events (BeforeUnloadEvent cannot be constructed)
        case "beforeunload":
            return [Event, mapEvent, CANCELABLE];
        case "unload":
            return [Event, mapEvent];

        // Default: base Event constructor
        default:
            return [Event, mapEvent, BUBBLES];
    }
};

/**
 * @param {Node} [a]
 * @param {Node} [b]
 */
const getFirstCommonParent = (a, b) => {
    if (!a || !b || a.ownerDocument !== b.ownerDocument) {
        return null;
    }

    const range = document.createRange();
    range.setStart(a, 0);
    range.setEnd(b, 0);

    if (range.collapsed) {
        // Re-arranges range if the first node comes after the second
        range.setStart(b, 0);
        range.setEnd(a, 0);
    }

    return range.commonAncestorContainer;
};

/**
 * @param {HTMLElement} element
 * @param {PointerOptions} [options]
 */
const getPosition = (element, options) => {
    const { position, relative } = options || {};
    const isString = typeof position === "string";
    const [posX, posY] = parsePosition(position);

    if (!isString && !relative && !$isNaN(posX) && !$isNaN(posY)) {
        // Absolute position
        return toEventPosition(posX, posY, position);
    }

    const { x, y, width, height } = getNodeRect(element);
    let clientX = x;
    let clientY = y;

    if (isString) {
        const positions = position.split("-");

        // X position
        if (positions.includes("left")) {
            clientX -= 1;
        } else if (positions.includes("right")) {
            clientX += $ceil(width) + 1;
        } else {
            clientX += width / 2;
        }

        // Y position
        if (positions.includes("top")) {
            clientY -= 1;
        } else if (positions.includes("bottom")) {
            clientY += $ceil(height) + 1;
        } else {
            clientY += height / 2;
        }
    } else {
        // X position
        if ($isNaN(posX)) {
            clientX += width / 2;
        } else {
            if (relative) {
                clientX += posX || 0;
            } else {
                clientX = posX || 0;
            }
        }

        // Y position
        if ($isNaN(posY)) {
            clientY += height / 2;
        } else {
            if (relative) {
                clientY += posY || 0;
            } else {
                clientY = posY || 0;
            }
        }
    }

    return toEventPosition(clientX, clientY, position);
};

/**
 * @param {Node} target
 */
const getStringSelection = (target) =>
    $isInteger(target.selectionStart) &&
    $isInteger(target.selectionEnd) &&
    [target.selectionStart, target.selectionEnd].join(",");

/**
 * @param {Node} node
 * @param  {...string} tagNames
 */
const hasTagName = (node, ...tagNames) => tagNames.includes(getTag(node));

const hasTouch = () =>
    globalThis.ontouchstart !== undefined || globalThis.matchMedia("(pointer:coarse)").matches;

/**
 * @param {EventTarget | EventPosition} target
 * @param {PointerOptions} [options]
 */
const isDifferentPosition = (target, options) => {
    const previous = runTime.position;
    const next = isNode(target) ? getPosition(target, options) : target;
    for (const key in next) {
        if (previous[key] !== next[key]) {
            return true;
        }
    }
    return false;
};

/**
 * @param {unknown} value
 */
const isNil = (value) => value === null || value === undefined;

/**
 * @param {Event} event
 */
const isPrevented = (event) => event && event.defaultPrevented;

/**
 * @param {KeyStrokes} keyStrokes
 * @param {KeyboardEventInit} [options]
 * @returns {KeyboardEventInit}
 */
const parseKeyStrokes = (keyStrokes, options) =>
    (isIterable(keyStrokes) ? [...keyStrokes] : [keyStrokes]).map((key) => {
        const lower = key.toLowerCase();
        return {
            ...options,
            key: lower.length === 1 ? key : KEY_ALIASES[lower] || key,
        };
    });

/**
 * Redirects all 'submit' events to explicit network requests.
 *
 * This allows the `mockFetch` helper to take control over submit requests.
 *
 * @param {SubmitEvent} ev
 */
const redirectSubmit = (ev) => {
    if (isPrevented(ev)) {
        return;
    }

    ev.preventDefault();

    /** @type {HTMLFormElement} */
    const form = ev.target;

    globalThis.fetch(form.action, {
        method: form.method,
        body: new FormData(form, ev.submitter),
    });
};

/**
 * @param {PointerEventInit} eventInit
 * @param {boolean} toggle
 */
const registerButton = (eventInit, toggle) => {
    let value = 0;
    switch (eventInit.button) {
        case btn.LEFT: {
            // Main button (left button)
            value = 1;
            break;
        }
        case btn.MIDDLE: {
            // Auxiliary button (middle button)
            value = 4;
            break;
        }
        case btn.RIGHT: {
            // Secondary button (right button)
            value = 2;
            break;
        }
        case btn.BACK: {
            // Fourth button (Browser Back)
            value = 8;
            break;
        }
        case btn.FORWARD: {
            // Fifth button (Browser Forward)
            value = 16;
            break;
        }
    }

    runTime.buttons = $max(runTime.buttons + (toggle ? value : -value), 0);
};

/**
 * @param {Event} ev
 */
const registerFileInput = ({ target }) => {
    if (getTag(target) === "input" && target.type === "file") {
        runTime.fileInput = target;
    } else {
        runTime.fileInput = null;
    }
};

/**
 * @param {EventTarget} target
 * @param {string} initialValue
 * @param {ConfirmAction} confirmAction
 */
const registerForChange = async (target, initialValue, confirmAction) => {
    const dispatchChange = () => target.value !== initialValue && dispatch(target, "change");

    confirmAction &&= confirmAction.toLowerCase();
    if (confirmAction === "auto") {
        confirmAction = getTag(target) === "input" ? "enter" : "blur";
    }
    if (getTag(target) === "input") {
        changeTargetListeners.push(
            on(target, "keydown", (ev) => {
                if (isPrevented(ev) || ev.key !== "Enter") {
                    return;
                }
                removeChangeTargetListeners();
                afterNextDispatch = dispatchChange;
            })
        );
    } else if (confirmAction === "enter") {
        throw new HootDomError(`"enter" confirm action is only supported on <input/> elements`);
    }

    changeTargetListeners.push(
        on(target, "blur", () => {
            removeChangeTargetListeners();
            dispatchChange();
        }),
        on(target, "change", removeChangeTargetListeners)
    );

    switch (confirmAction) {
        case "blur": {
            await _click(getDocument(target).body, {
                position: { x: 0, y: 0 },
            });
            break;
        }
        case "enter": {
            await _press(target, { key: "Enter" });
            break;
        }
        case "tab": {
            await _press(target, { key: "Tab" });
            break;
        }
    }
};

/**
 * @param {KeyboardEventInit} eventInit
 * @param {boolean} toggle
 */
const registerSpecialKey = (eventInit, toggle) => {
    switch (eventInit.key) {
        case "Alt": {
            runTime.modifierKeys.altKey = toggle;
            break;
        }
        case "Control": {
            runTime.modifierKeys.ctrlKey = toggle;
            break;
        }
        case "Meta": {
            runTime.modifierKeys.metaKey = toggle;
            break;
        }
        case "Shift": {
            runTime.modifierKeys.shiftKey = toggle;
            break;
        }
    }
};

const removeChangeTargetListeners = () => {
    while (changeTargetListeners.length) {
        changeTargetListeners.pop()();
    }
};

/**
 * @param {HTMLElement | null} target
 */
const setPointerDownTarget = (target) => {
    if (runTime.pointerDownTarget) {
        runTime.previousPointerDownTarget = runTime.pointerDownTarget;
    }
    runTime.pointerDownTarget = target;
    runTime.canStartDrag = false;
};

/**
 * @param {HTMLElement | null} target
 * @param {PointerOptions} [options]
 */
const setPointerTarget = async (target, options) => {
    runTime.previousPointerTarget = runTime.pointerTarget;
    runTime.pointerTarget = target;

    if (runTime.pointerTarget !== runTime.previousPointerTarget && runTime.canStartDrag) {
        /**
         * Special action: drag start
         *  On: unprevented 'pointerdown' on a draggable element (DESKTOP ONLY)
         *  Do: triggers a 'dragstart' event
         */
        const dragStartEvent = await dispatch(runTime.previousPointerTarget, "dragstart");

        runTime.isDragging = !isPrevented(dragStartEvent);
        runTime.canStartDrag = false;
    }

    runTime.position = target && getPosition(target, options);
};

/**
 * @param {string} type
 * @param {EventOptions} type
 */
const setupEvents = (type, options) => {
    currentEventTypes.push(type);
    $assign(currentEventInit, options?.eventInit);

    return async () => {
        for (const eventType in currentEventInit) {
            delete currentEventInit[eventType];
        }
        const events = new EventList(getCurrentEvents());
        const currentType = currentEventTypes.pop();
        delete currentEvents[currentType];
        if (!allowLogs) {
            return events;
        }
        const groupName = [`${type}: dispatched`, events.length, `events`];
        $groupCollapsed(...groupName);
        for (const event of events) {
            /** @type {(keyof typeof LOG_COLORS)[]} */
            const colors = ["blue"];

            const typeList = [event.type];
            if (event.key) {
                typeList.push(event.key);
            } else if (event.button) {
                typeList.push(event.button);
            }
            [...Array(typeList.length)].forEach(() => colors.push("orange"));

            const typeString = typeList.map((t) => `%c"${t}"%c`).join(", ");
            let message = `%c${event.constructor.name}%c<${typeString}>`;
            if (event.__bubbleCount) {
                message += ` (${event.__bubbleCount})`;
            }
            const target = event.__originalTarget || event.target;
            if (isNode(target)) {
                const targetParts = toSelector(target, { object: true });
                colors.push("blue");
                if (targetParts.id) {
                    colors.push("orange");
                }
                if (targetParts.class) {
                    colors.push("lightBlue");
                }
                const targetString = $values(targetParts)
                    .map((part) => `%c${part}%c`)
                    .join("");
                message += ` @${targetString}`;
            }
            const messageColors = colors.flatMap((color) => [
                `color: ${LOG_COLORS[color]}; font-weight: normal`,
                `color: ${LOG_COLORS.reset}`,
            ]);

            $groupCollapsed(message, ...messageColors);
            $dir(event);
            $log(target);
            $groupEnd();
        }
        $groupEnd();

        return events;
    };
};

/**
 * @param {number} clientX
 * @param {number} clientY
 * @param {Partial<EventPosition>} [position]
 */
const toEventPosition = (clientX, clientY, position) => {
    clientX ||= 0;
    clientY ||= 0;
    return {
        clientX,
        clientY,
        pageX: position?.pageX ?? clientX,
        pageY: position?.pageY ?? clientY,
        screenX: position?.screenX ?? clientX,
        screenY: position?.screenY ?? clientY,
    };
};

/**
 * @param {EventTarget} target
 * @param {PointerEventInit} pointerInit
 */
const triggerClick = async (target, pointerInit) => {
    if (target.disabled) {
        return;
    }
    const eventType = (pointerInit.button ?? 0) === btn.LEFT ? "click" : "auxclick";
    const clickEvent = await dispatch(target, eventType, pointerInit);
    if (isPrevented(clickEvent)) {
        return;
    }
    if (isFirefox()) {
        // Thanks Firefox
        switch (getTag(target)) {
            case "label": {
                /**
                 * @firefox
                 * Special action: label 'Click'
                 *  On: unprevented 'click' on a <label/>
                 *  Do: triggers a 'click' event on the first <input/> descendant
                 */
                target = target.control;
                if (target) {
                    await triggerClick(target, pointerInit);
                }
                break;
            }
            case "option": {
                /**
                 * @firefox
                 * Special action: option 'Click'
                 *  On: unprevented 'click' on an <option/>
                 *  Do: triggers a 'change' event on the parent <select/>
                 */
                const parent = target.parentElement;
                if (parent && getTag(parent) === "select") {
                    await dispatch(parent, "change");
                }
                break;
            }
        }
    }
};

/**
 * @param {EventTarget} target
 * @param {DragEventInit} eventInit
 */
const triggerDrag = async (target, eventInit) => {
    await dispatch(target, "drag", eventInit);
    // Only "dragover" being prevented is taken into account for "drop" events
    const dragOverEvent = await dispatch(target, "dragover", eventInit);
    runTime.lastDragOverCancelled = isPrevented(dragOverEvent);
};

/**
 * @param {EventTarget} target
 */
const triggerFocus = async (target) => {
    const previous = getActiveElement(target);
    if (previous === target) {
        return;
    }
    if (previous !== target.ownerDocument.body) {
        await dispatchAndIgnore({
            target: previous,
            events: ["blur", "focusout"],
            callback: (el) => el.blur(),
            options: { relatedTarget: target },
        });
    }
    if (isNodeFocusable(target)) {
        const previousSelection = getStringSelection(target);
        await dispatchAndIgnore({
            target,
            events: ["focus", "focusin"],
            additionalEvents: ["select"],
            callback: (el) => el.focus(),
            options: { relatedTarget: previous },
        });
        if (previousSelection && previousSelection === getStringSelection(target)) {
            changeSelection(target, target.value.length, target.value.length);
        }
    }
};

/**
 * @param {EventTarget} target
 * @param {FillOptions} [options]
 */
const _clear = async (target, options) => {
    // Inputs and text areas
    const initialValue = target.value;

    // Simulates 2 key presses:
    // - Control + A: selects all the text
    // - Backspace: deletes the text
    fullClear = true;
    await _press(target, { ctrlKey: true, key: "a" });
    await _press(target, { key: "Backspace" });
    fullClear = false;

    await registerForChange(target, initialValue, options?.confirm);
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} [options]
 */
const _click = async (target, options) => {
    await _pointerDown(target, options);
    await _pointerUp(target, options);
};

/**
 * @param {EventTarget} target
 * @param {InputValue} value
 * @param {FillOptions} [options]
 */
const _fill = async (target, value, options) => {
    const initialValue = target.value;

    if (getTag(target) === "input") {
        switch (target.type) {
            case "color": {
                target.value = String(value);
                await dispatch(target, "input");
                await dispatch(target, "change");
                return;
            }
            case "file": {
                const dataTransfer = new DataTransfer();
                const files = ensureArray(value);
                if (files.length > 1 && !target.multiple) {
                    throw new HootDomError(`input[type="file"] does not support multiple files`);
                }
                for (const file of files) {
                    if (!(file instanceof File)) {
                        throw new TypeError(`file input only accept 'File' objects`);
                    }
                    dataTransfer.items.add(file);
                }
                target.files = dataTransfer.files;

                await dispatch(target, "change");
                return;
            }
            case "range": {
                const numberValue = $parseFloat(value);
                if ($isNaN(numberValue)) {
                    throw new TypeError(`input[type="range"] only accept 'number' values`);
                }

                target.value = String(numberValue);
                await dispatch(target, "input");
                await dispatch(target, "change");
                return;
            }
        }
    }

    if (options?.instantly) {
        // Simulates filling the clipboard with the value (can be from external source)
        globalThis.navigator.clipboard.writeText(value).catch();
        await _press(target, { ctrlKey: true, key: "v" });
    } else {
        if (options?.composition) {
            runTime.isComposing = true;
            // Simulates the start of a composition
            await dispatch(target, "compositionstart");
        }
        for (const char of String(value)) {
            const key = char.toLowerCase();
            await _press(target, { key, shiftKey: key !== char });
        }
        if (options?.composition) {
            runTime.isComposing = false;
            // Simulates the end of a composition
            await dispatch(target, "compositionend");
        }
    }

    await registerForChange(target, initialValue, options?.confirm);
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} [options]
 */
const _hover = async (target, options) => {
    const isDifferentTarget = target !== runTime.pointerTarget;
    const previousPosition = runTime.position;

    await setPointerTarget(target, options);

    const { previousPointerTarget: previous, pointerTarget: current } = runTime;
    if (isDifferentTarget && previous && (!current || !previous.contains(current))) {
        // Leaves previous target
        const leaveEventInit = {
            ...previousPosition,
            relatedTarget: current,
        };

        if (runTime.isDragging) {
            // If dragging, only drag events are triggered
            await triggerDrag(previous, leaveEventInit);
            await dispatch(previous, "dragleave", leaveEventInit);
        } else {
            // Regular case: pointer events are triggered
            await dispatchPointerEvent(previous, "pointermove", leaveEventInit, {
                mouse: ["mousemove"],
                touch: ["touchmove"],
            });
            await dispatchPointerEvent(previous, "pointerout", leaveEventInit, {
                mouse: ["mouseout"],
            });
            const leaveEvents = await Promise.all(
                getDifferentParents(current, previous).map((element) =>
                    dispatch(element, "pointerleave", leaveEventInit)
                )
            );
            if (!hasTouch()) {
                await dispatchRelatedEvents(leaveEvents, "mouseleave", leaveEventInit);
            }
        }
    }

    if (current) {
        const enterEventInit = {
            ...runTime.position,
            relatedTarget: previous,
        };
        if (runTime.isDragging) {
            // If dragging, only drag events are triggered
            if (isDifferentTarget) {
                await dispatch(target, "dragenter", enterEventInit);
            }
            await triggerDrag(target, enterEventInit);
        } else {
            // Regular case: pointer events are triggered
            if (isDifferentTarget) {
                await dispatchPointerEvent(target, "pointerover", enterEventInit, {
                    mouse: ["mouseover"],
                });
                const enterEvents = await Promise.all(
                    getDifferentParents(previous, current).map((element) =>
                        dispatch(element, "pointerenter", enterEventInit)
                    )
                );
                if (!hasTouch()) {
                    await dispatchRelatedEvents(enterEvents, "mouseenter", enterEventInit);
                }
            }
            await dispatchPointerEvent(target, "pointermove", enterEventInit, {
                mouse: ["mousemove"],
                touch: ["touchmove"],
            });
        }
    }
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} [options]
 */
const _implicitHover = async (target, options) => {
    if (runTime.pointerTarget !== target || isDifferentPosition(target, options)) {
        await _hover(target, options);
    }
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _keyDown = async (target, eventInit) => {
    eventInit = { ...eventInit, ...currentEventInit.keydown };
    registerSpecialKey(eventInit, true);

    const repeat =
        typeof eventInit.repeat === "boolean" ? eventInit.repeat : runTime.key === eventInit.key;
    runTime.key = eventInit.key;
    const keyDownEvent = await dispatch(target, "keydown", { ...eventInit, repeat });

    if (isPrevented(keyDownEvent)) {
        return;
    }

    /**
     * @param {string} toInsert
     * @param {string} type
     */
    const insertValue = (toInsert, type) => {
        const { selectionStart, selectionEnd, value } = target;
        inputData = toInsert;
        inputType = type;
        if (isNil(selectionStart) && isNil(selectionEnd)) {
            nextValue += toInsert;
        } else {
            nextValue = value.slice(0, selectionStart) + toInsert + value.slice(selectionEnd);
            if (selectionStart === selectionEnd) {
                nextSelectionStart = nextSelectionEnd = selectionStart + 1;
            }
        }
    };

    const { ctrlKey, key, shiftKey } = keyDownEvent;
    const initialValue = target.value;
    let inputData = null;
    let inputType = null;
    let nextSelectionEnd = null;
    let nextSelectionStart = null;
    let nextValue = initialValue;
    let triggerSelect = false;

    if (isEditable(target)) {
        switch (key) {
            case "ArrowDown":
            case "ArrowLeft":
            case "ArrowUp":
            case "ArrowRight": {
                const { selectionStart, selectionEnd, value } = target;
                if (isNil(selectionStart) || isNil(selectionEnd)) {
                    break;
                }
                const start = key === "ArrowLeft" || key === "ArrowUp";
                let selectionTarget;
                if (ctrlKey) {
                    // Move to the start/end of the line
                    selectionTarget = start ? 0 : value.length;
                } else {
                    // Move the cursor left or right
                    selectionTarget = start ? selectionStart - 1 : selectionEnd + 1;
                }
                nextSelectionStart = nextSelectionEnd = $max(
                    $min(selectionTarget, value.length),
                    0
                );
                triggerSelect = shiftKey;
                break;
            }
            case "Backspace": {
                const { selectionStart, selectionEnd, value } = target;
                if (fullClear) {
                    // Remove all characters
                    nextValue = "";
                } else if (isNil(selectionStart) || isNil(selectionEnd)) {
                    // Remove last character
                    nextValue = value.slice(0, -1);
                } else if (selectionStart === selectionEnd) {
                    // Remove previous character from target value
                    nextValue = value.slice(0, selectionStart - 1) + value.slice(selectionEnd);
                } else {
                    // Remove current selection from target value
                    nextValue = deleteSelection(target);
                }
                inputType = "deleteContentBackward";
                break;
            }
            case "Delete": {
                const { selectionStart, selectionEnd, value } = target;
                if (fullClear) {
                    // Remove all characters
                    nextValue = "";
                } else if (isNil(selectionStart) || isNil(selectionEnd)) {
                    // Remove first character
                    nextValue = value.slice(1);
                } else if (selectionStart === selectionEnd) {
                    // Remove next character from target value
                    nextValue = value.slice(0, selectionStart) + value.slice(selectionEnd + 1);
                } else {
                    // Remove current selection from target value
                    nextValue = deleteSelection(target);
                }
                inputType = "deleteContentForward";
                break;
            }
            case "Enter": {
                if (target.tagName === "TEXTAREA") {
                    // Insert new line
                    insertValue("\n", "insertLineBreak");
                }
                break;
            }
            default: {
                if (key.length === 1 && !ctrlKey) {
                    // Character coming from the keystroke
                    // ! TODO: Doesn't work with non-roman locales
                    insertValue(
                        shiftKey ? key.toUpperCase() : key.toLowerCase(),
                        runTime.isComposing ? "insertCompositionText" : "insertText"
                    );
                }
            }
        }
    }

    switch (key) {
        case "a": {
            if (ctrlKey) {
                // Select all
                if (isEditable(target)) {
                    nextSelectionStart = 0;
                    nextSelectionEnd = target.value.length;
                    triggerSelect = true;
                } else {
                    const selection = globalThis.getSelection();
                    const range = $createRange();
                    range.selectNodeContents(target);
                    selection.removeAllRanges();
                    selection.addRange(range);
                }
            }
            break;
        }
        /**
         * Special action: copy
         *  On: unprevented 'Control + c' keydown
         *  Do: copy current selection to clipboard
         */
        case "c": {
            if (ctrlKey) {
                // Get selection from window
                const text = globalThis.getSelection().toString();
                globalThis.navigator.clipboard.writeText(text).catch();

                await dispatch(target, "copy", {
                    clipboardData: eventInit.dataTransfer || new DataTransfer(),
                });
            }
            break;
        }
        case "Enter": {
            const tag = getTag(target);
            const parentForm = target.closest("form");
            if (parentForm && target.type !== "button") {
                /**
                 * Special action: <form> 'Enter'
                 *  On: unprevented 'Enter' keydown on any element that
                 *      is not a <button type="button"/> in a form element
                 *  Do: triggers a 'submit' event on the form
                 */
                await dispatch(parentForm, "submit");
            } else if (
                !keyDownEvent.repeat &&
                (tag === "a" || tag === "button" || (tag === "input" && target.type === "button"))
            ) {
                /**
                 * Special action: <a>, <button> or <input type="button"> 'Enter'
                 *  On: unprevented and unrepeated 'Enter' keydown on mentioned elements
                 *  Do: triggers a 'click' event on the element
                 */
                await dispatch(target, "click", { button: btn.LEFT });
            }
            break;
        }
        case "Escape": {
            runTime.isDragging = false;
            break;
        }
        /**
         * Special action: shift focus
         *  On: unprevented 'Tab' keydown
         *  Do: focus next (or previous with 'Shift') focusable element
         */
        case "Tab": {
            const next = shiftKey
                ? getPreviousFocusableElement({ tabbable: true })
                : getNextFocusableElement({ tabbable: true });
            if (next) {
                await triggerFocus(next);
            }
            break;
        }
        /**
         * Special action: paste
         *  On: unprevented 'Control + v' keydown on editable element
         *  Do: paste current clipboard content to current element
         */
        case "v": {
            if (ctrlKey && isEditable(target)) {
                // Set target value (if possible)
                try {
                    nextValue = await globalThis.navigator.clipboard.readText();
                } catch (err) {}
                inputType = "insertFromPaste";

                await dispatch(target, "paste", {
                    clipboardData: eventInit.dataTransfer || new DataTransfer(),
                });
            }
            break;
        }
        /**
         * Special action: cut
         *  On: unprevented 'Control + x' keydown on editable element
         *  Do: cut current selection to clipboard and remove selection
         */
        case "x": {
            if (ctrlKey && isEditable(target)) {
                // Get selection from window
                const text = globalThis.getSelection().toString();
                globalThis.navigator.clipboard.writeText(text).catch();

                nextValue = deleteSelection(target);
                inputType = "deleteByCut";

                await dispatch(target, "cut", {
                    clipboardData: eventInit.dataTransfer || new DataTransfer(),
                });
            }
            break;
        }
    }

    if (initialValue !== nextValue) {
        target.value = nextValue;
        const inputEventInit = {
            data: inputData,
            inputType,
        };
        const beforeInputEvent = await dispatch(target, "beforeinput", inputEventInit);
        if (!isPrevented(beforeInputEvent)) {
            await dispatch(target, "input", inputEventInit);
        }
    }
    changeSelection(target, nextSelectionStart, nextSelectionEnd);
    if (triggerSelect) {
        await dispatchAndIgnore({
            target,
            events: ["select"],
        });
    }
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _keyUp = async (target, eventInit) => {
    eventInit = { ...eventInit, ...currentEventInit.keyup };
    await dispatch(target, "keyup", eventInit);

    runTime.key = null;
    registerSpecialKey(eventInit, false);

    if (eventInit.key === " " && getTag(target) === "input" && target.type === "checkbox") {
        /**
         * Special action: input[type=checkbox] 'Space'
         *  On: unprevented ' ' keydown on an <input type="checkbox"/>
         *  Do: triggers a 'click' event on the input
         */
        await triggerClick(target, { button: btn.LEFT });
    }
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} [options]
 */
const _pointerDown = async (target, options) => {
    setPointerDownTarget(target);

    const pointerDownTarget = runTime.pointerDownTarget;
    const eventInit = {
        ...runTime.position,
        ...currentEventInit.pointerdown,
        button: options?.button || btn.LEFT,
    };

    registerButton(eventInit, true);

    if (pointerDownTarget !== runTime.previousPointerDownTarget) {
        runTime.clickCount = 0;
    }

    runTime.touchStartPosition = { ...runTime.position };
    runTime.touchStartTimeOffset = globalThis.Date.now();
    const prevented = await dispatchPointerEvent(pointerDownTarget, "pointerdown", eventInit, {
        mouse: !pointerDownTarget.disabled && [
            "mousedown",
            { ...eventInit, detail: runTime.clickCount + 1 },
        ],
        touch: ["touchstart"],
    });

    if (prevented) {
        return;
    }

    // Focus the element (if focusable)
    await triggerFocus(target);

    if (eventInit.button === btn.LEFT && !hasTouch() && pointerDownTarget.draggable) {
        runTime.canStartDrag = true;
    } else if (eventInit.button === btn.RIGHT) {
        /**
         * Special action: context menu
         *  On: unprevented 'pointerdown' with right click and its related
         *      event on an element
         *  Do: triggers a 'contextmenu' event
         */
        await dispatch(target, "contextmenu", eventInit);
    }
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} [options]
 */
const _pointerUp = async (target, options) => {
    const isLongTap = globalThis.Date.now() - runTime.touchStartTimeOffset > LONG_TAP_DELAY;
    const pointerDownTarget = runTime.pointerDownTarget;
    const eventInit = {
        ...runTime.position,
        ...currentEventInit.pointerup,
        button: options?.button || btn.LEFT,
    };

    registerButton(eventInit, false);

    if (runTime.isDragging) {
        // If dragging, only drag events are triggered
        runTime.isDragging = false;
        if (runTime.lastDragOverCancelled) {
            /**
             * Special action: drop
             * - On: prevented 'dragover'
             * - Do: triggers a 'drop' event on the target
             */
            await dispatch(target, "drop", eventInit);
        }

        await dispatch(target, "dragend", eventInit);
        return;
    }

    const mouseEventInit = {
        ...eventInit,
        detail: runTime.clickCount + 1,
    };
    await dispatchPointerEvent(target, "pointerup", eventInit, {
        mouse: !target.disabled && ["mouseup", mouseEventInit],
        touch: ["touchend"],
    });

    const touchStartPosition = runTime.touchStartPosition;
    runTime.touchStartPosition = {};

    if (hasTouch() && (isDifferentPosition(touchStartPosition) || isLongTap)) {
        // No further event is triggered:
        // there was a swiping motion since the "touchstart" event
        // or a long press was detected.
        return;
    }

    let actualTarget;
    if (hasTouch()) {
        actualTarget = pointerDownTarget === target && target;
    } else {
        actualTarget = getFirstCommonParent(target, pointerDownTarget);
    }
    if (actualTarget) {
        await triggerClick(actualTarget, mouseEventInit);
        if (mouseEventInit.button === btn.LEFT) {
            runTime.clickCount++;
            if (!hasTouch() && runTime.clickCount % 2 === 0) {
                await dispatch(actualTarget, "dblclick", mouseEventInit);
            }
        }
    }

    setPointerDownTarget(null);
    if (runTime.pointerDownTimeout) {
        globalThis.clearTimeout(runTime.pointerDownTimeout);
    }
    runTime.pointerDownTimeout = globalThis.setTimeout(() => {
        // Use `globalThis.setTimeout` to potentially make use of the mock timeouts
        // since the events run in the same temporal context as the tests
        runTime.clickCount = 0;
        runTime.pointerDownTimeout = 0;
    }, DOUBLE_CLICK_DELAY);
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _press = async (target, eventInit) => {
    await _keyDown(target, eventInit);
    await _keyUp(target, eventInit);
};

/**
 * @param {EventTarget} target
 * @param {string | number | (string | number)[]} value
 */
const _select = async (target, value) => {
    const values = ensureArray(value).map(String);
    let found = false;
    for (const option of target.options) {
        option.selected = values.includes(option.value);
        found ||= option.selected;
    }
    if (!value) {
        target.selectedIndex = -1;
    } else if (!found) {
        throw new HootDomError(
            `error when calling \`select()\`: no option found with value "${values.join(", ")}"`
        );
    }
    await dispatch(target, "change");
};

const btn = {
    LEFT: 0,
    MIDDLE: 1,
    RIGHT: 2,
    BACK: 3,
    FORWARD: 4,
};
const CAPTURE = { capture: true };
const DEPRECATED_EVENT_PROPERTIES = {
    keyCode: "key",
    which: "key",
};
const DEPRECATED_EVENTS = {
    keypress: "keydown",
    mousewheel: "wheel",
};
const DOUBLE_CLICK_DELAY = 500;

/**
 * Ignore certain trusted events (dispatched by `focus()`, `scroll()`, etc.)
 * @type {[EventType, (event: Event) => any, AddEventListenerOptions][]}
 */
const GLOBAL_TRUSTED_EVENTS_CANCELERS = [
    ["blur", cancelTrustedEvent, CAPTURE],
    ["focus", cancelTrustedEvent, CAPTURE],
    ["focusin", cancelTrustedEvent, CAPTURE],
    ["focusout", cancelTrustedEvent, CAPTURE],
    ["scroll", cancelTrustedEvent, CAPTURE],
    ["scrollend", cancelTrustedEvent, CAPTURE],
    ["select", cancelTrustedEvent, CAPTURE],
];
/**
 * Register file input on click & focus events
 * @type {[EventType, (event: Event) => any, AddEventListenerOptions][]}
 */
const GLOBAL_FILE_INPUT_REGISTERERS = [
    ["click", registerFileInput, CAPTURE],
    ["focus", registerFileInput, CAPTURE],
];
/**
 * Redirect events to other features
 * @type {[EventType, (event: Event) => any, AddEventListenerOptions][]}
 */
const GLOBAL_SUBMIT_FORWARDERS = [["submit", redirectSubmit]];

const KEY_ALIASES = {
    // case insensitive aliases
    alt: "Alt",
    arrowdown: "ArrowDown",
    arrowleft: "ArrowLeft",
    arrowright: "ArrowRight",
    arrowup: "ArrowUp",
    backspace: "Backspace",
    control: "Control",
    delete: "Delete",
    enter: "Enter",
    escape: "Escape",
    meta: "Meta",
    shift: "Shift",
    tab: "Tab",

    // Other aliases
    caps: "Shift",
    cmd: "Meta",
    command: "Meta",
    ctrl: "Control",
    del: "Delete",
    down: "ArrowDown",
    esc: "Escape",
    left: "ArrowLeft",
    right: "ArrowRight",
    space: " ",
    up: "ArrowUp",
    win: "Meta",
};
const LOG_COLORS = {
    blue: "#5db0d7",
    orange: "#f29364",
    lightBlue: "#9bbbdc",
    reset: "inherit",
};
const LONG_TAP_DELAY = 500;

/** @type {Record<string, Event[]>} */
const currentEvents = $create(null);
/** @type {Record<EventType, EventInit>} */
const currentEventInit = $create(null);
/** @type {string[]} */
const currentEventTypes = [];
/** @type {(() => Promise<void>) | null} */
let afterNextDispatch = null;
let allowLogs = false;
let fullClear = false;

// Keyboard global variables
const changeTargetListeners = [];

// Other global variables
const runTime = getDefaultRunTimeValue();

//-----------------------------------------------------------------------------
// Event init attributes mappers
//-----------------------------------------------------------------------------

const BUBBLES = 0b1;
const CANCELABLE = 0b10;
const VIEW = 0b100;

// Generic mappers
// ---------------

/**
 * - does not bubble
 * - cannot be canceled
 * @param {FullEventInit} eventInit
 */
const mapEvent = (eventInit) => eventInit;

// Pointer, mouse & wheel event mappers
// ------------------------------------

/**
 * @param {FullEventInit<MouseEventInit>} eventInit
 */
const mapMouseEvent = (eventInit) => ({
    button: -1,
    buttons: runTime.buttons,
    clientX: eventInit.clientX ?? eventInit.pageX ?? eventInit.screenX ?? 0,
    clientY: eventInit.clientY ?? eventInit.pageY ?? eventInit.screenY ?? 0,
    ...runTime.modifierKeys,
    ...eventInit,
});

/**
 * @param {FullEventInit<PointerEventInit>} eventInit
 */
const mapPointerEvent = (eventInit) => ({
    ...mapMouseEvent(eventInit),
    button: btn.LEFT,
    pointerId: 1,
    pointerType: hasTouch() ? "touch" : "mouse",
    ...eventInit,
});

/**
 * @param {FullEventInit<WheelEventInit>} eventInit
 */
const mapWheelEvent = (eventInit) => ({
    ...mapMouseEvent(eventInit),
    button: btn.LEFT,
    ...eventInit,
});

// Touch event mappers
// -------------------

/**
 * @param {FullEventInit<TouchEventInit>} eventInit
 */
const mapTouchEvent = (eventInit) => {
    const touches = eventInit.targetTouches ||
        eventInit.touches || [new Touch({ identifier: 0, ...eventInit })];
    return {
        ...eventInit,
        changedTouches: eventInit.changedTouches || touches,
        target: eventInit.target,
        targetTouches: eventInit.targetTouches || touches,
        touches: eventInit.touches || (eventInit.type === "touchend" ? [] : touches),
    };
};

// Keyboard & input event mappers
// ------------------------------

/**
 * @param {FullEventInit<InputEventInit>} eventInit
 */
const mapInputEvent = (eventInit) => ({
    data: null,
    isComposing: Boolean(runTime.isComposing),
    ...eventInit,
});

/**
 * @param {FullEventInit<KeyboardEventInit>} eventInit
 */
const mapKeyboardEvent = (eventInit) => ({
    isComposing: Boolean(runTime.isComposing),
    ...runTime.modifierKeys,
    ...eventInit,
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Ensures that the given {@link AsyncTarget} is checked.
 *
 * If it is not checked, a click is simulated on the input.
 * If the input is still not checked after the click, an error is thrown.
 *
 * @see {@link click}
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  check("input[type=checkbox]"); // Checks the first <input> checkbox element
 */
export async function check(target, options) {
    const finalizeEvents = setupEvents("check", options);
    const element = queryFirst(await target, options);
    if (!isCheckable(element)) {
        throw new HootDomError(
            `cannot call \`check()\`: target should be a checkbox or radio input`
        );
    }

    const checkTarget = getTag(element) === "label" ? element.control : element;
    if (!checkTarget.checked) {
        await _implicitHover(element, options);
        await _click(element, options);

        if (!checkTarget.checked) {
            throw new HootDomError(
                `error when calling \`check()\`: target is not checked after interaction`
            );
        }
    }

    return finalizeEvents();
}

/**
 * Clears the **value** of the current **active element**.
 *
 * This is done using the following sequence:
 * - pressing "Control" + "A" to select the whole value;
 * - pressing "Backspace" to delete the value;
 * - (optional) triggering a "change" event by pressing "Enter".
 *
 * @param {FillOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  clear(); // Clears the value of the current active element
 */
export async function clear(options) {
    const finalizeEvents = setupEvents("clear", options);
    const element = getActiveElement();

    if (!hasTagName(element, "select") && !isEditable(element)) {
        throw new HootDomError(
            `cannot call \`clear()\`: target should be editable or a <select> element`
        );
    }

    if (isEditable(element)) {
        await _clear(element, options);
    } else {
        // Selects
        await _select(element, "");
    }

    return finalizeEvents();
}

/**
 * Performs a click sequence on the given {@link AsyncTarget}.
 *
 * The event sequence is as follows:
 *  - `pointerdown`
 *  - [desktop] `mousedown`
 *  - [touch] `touchstart`
 *  - [target is not active element] `blur`
 *  - [target is focusable] `focus`
 *  - `pointerup`
 *  - [desktop] `mouseup`
 *  - [touch] `touchend`
 *  - `click`
 *  - `dblclick` if click is not prevented & current click count is even
 *
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  click("button"); // Clicks on the first <button> element
 */
export async function click(target, options) {
    const finalizeEvents = setupEvents("click", options);
    const element = queryFirst(await target, options);

    await _implicitHover(element, options);
    await _click(element, options);

    return finalizeEvents();
}

/**
 * Performs two click sequences on the given {@link AsyncTarget}.
 *
 * @see {@link click}
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  dblclick("button"); // Double-clicks on the first <button> element
 */
export async function dblclick(target, options) {
    const finalizeEvents = setupEvents("dblclick", options);
    const element = queryFirst(await target, options);

    options = { ...options, button: btn.LEFT };
    await _implicitHover(element, options);
    await _click(element, options);
    await _click(element, options);

    return finalizeEvents();
}

/**
 * Creates a new DOM {@link Event} of the given type and dispatches it on the given
 * {@link Target}.
 *
 * Note that this function is free of side-effects and does not trigger any other
 * event or special action. It also only supports standard DOM events, and will
 * crash when trying to dispatch a non-standard or deprecated event.
 *
 * @template {EventType} T
 * @template {HTMLBodyElementEventMap[T]} I
 * @param {EventTarget} target
 * @param {T} type
 * @param {Partial<I> | { eventInit: Record<T, Partial<I>> }} [eventInit]
 * @example
 *  await dispatch(document.querySelector("input"), "paste"); // Dispatches a "paste" event on the given <input>
 * @returns {Promise<I>}
 */
export async function dispatch(target, type, eventInit) {
    if (type in DEPRECATED_EVENTS) {
        throw new HootDomError(
            `cannot dispatch "${type}" event: this event type is deprecated, use "${DEPRECATED_EVENTS[type]}" instead`
        );
    }
    if (type !== type.toLowerCase()) {
        throw new HootDomError(
            `cannot dispatch "${type}" event: this event type is either non-standard or deprecated`
        );
    }
    eventInit = { ...eventInit, ...currentEventInit[type] };
    for (const key in eventInit) {
        if (key in DEPRECATED_EVENT_PROPERTIES) {
            throw new HootDomError(
                `cannot dispatch "${type}" event: property "${key}" is deprecated, use "${DEPRECATED_EVENT_PROPERTIES[key]}" instead`
            );
        }
    }

    const [Constructor, processParams, flags] = getEventConstructor(type);
    const params = processParams({
        composed: true,
        ...eventInit,
        target,
        type,
    });
    if (flags & BUBBLES) {
        params.bubbles = true;
    }
    if (flags & CANCELABLE) {
        params.cancelable = true;
    }
    if (flags & VIEW) {
        params.view ||= getWindow(target);
    }
    const event = new Constructor(type, params);

    target.dispatchEvent(event);
    await Promise.resolve();

    getCurrentEvents().push(event);

    if (afterNextDispatch) {
        const callback = afterNextDispatch;
        afterNextDispatch = null;
        await microTick().then(callback);
    }

    return event;
}

/**
 * Starts a drag sequence on the given {@link AsyncTarget}.
 *
 * Returns a set of helper functions to direct the sequence:
 * - `moveTo`: moves the pointer to the given target;
 * - `drop`: drops the dragged element on the given target (if any);
 * - `cancel`: cancels the drag sequence.
 *
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<DragHelpers>}
 * @example
 *  drag(".card:first").drop(".card:last"); // Drags the first card onto the last one
 * @example
 *  drag(".card:first").moveTo(".card:last").drop(); // Same as above
 * @example
 *  const { cancel, moveTo } = await drag(".card:first"); // Starts the drag sequence
 *  moveTo(".card:eq(3)"); // Moves the dragged card to the 4th card
 *  cancel(); // Cancels the drag sequence
 */
export async function drag(target, options) {
    /**
     * @template T
     * @param {T} fn
     * @param {boolean} endDrag
     * @returns {T}
     */
    const expectIsDragging = (fn, endDrag) => {
        return {
            async [fn.name](...args) {
                if (dragEndReason) {
                    throw new HootDomError(
                        `cannot execute drag helper \`${fn.name}\`: drag sequence has been ended by \`${dragEndReason}\``
                    );
                }
                const result = await fn(...args);
                if (endDrag) {
                    dragEndReason = fn.name;
                }
                return result;
            },
        }[fn.name];
    };

    const cancel = expectIsDragging(
        /** @type {DragHelpers["cancel"]} */
        async function cancel(options) {
            const finalizeEvents = setupEvents("drag & drop: cancel", options);
            const element = getDocument().body;

            // Reset buttons
            runTime.buttons = 0;

            await _press(element, { key: "Escape" });

            dragEvents.push(...(await finalizeEvents()));

            return dragEvents;
        },
        true
    );

    const drop = expectIsDragging(
        /** @type {DragHelpers["drop"]} */
        async function drop(to, options) {
            if (to) {
                await moveTo(to, options);
            }

            const finalizeEvents = setupEvents("drag & drop: drop", options);

            await _pointerUp(runTime.pointerTarget, options);

            dragEvents.push(...(await finalizeEvents()));

            return dragEvents;
        },
        true
    );

    const moveTo = expectIsDragging(
        /** @type {DragHelpers["moveTo"]} */
        async function moveTo(to, options) {
            const finalizeEvents = setupEvents("drag & drop: move", options);

            await _hover(queryFirst(await to), options);

            dragEvents.push(...(await finalizeEvents()));

            return dragHelpers;
        },
        false
    );

    const finalizeEvents = setupEvents("drag & drop: start", options);
    const dragHelpers = { cancel, drop, moveTo };
    const element = queryFirst(await target);

    let dragEndReason = null;

    // Pointer down on main target
    await _implicitHover(element, options);
    await _pointerDown(element, options);

    const dragEvents = await finalizeEvents();

    return dragHelpers;
}

/**
 * Combination of {@link clear} and {@link fill}:
 * - first, clears the input value (if any)
 * - then fills the input with the given value
 *
 * @see {@link clear}
 * @see {@link fill}
 * @param {InputValue} value
 * @param {FillOptions} options
 * @returns {Promise<EventList>}
 * @example
 *  fill("foo"); // Types "foo" in the active element
 *  edit("Hello World"); // Replaces "foo" by "Hello World"
 */
export async function edit(value, options) {
    const finalizeEvents = setupEvents("edit", options);
    const element = getActiveElement();
    if (!isEditable(element)) {
        throw new HootDomError(`cannot call \`edit()\`: target should be editable`);
    }

    if (getNodeValue(element)) {
        await _clear(element);
    }
    await _fill(element, value, options);

    return finalizeEvents();
}

/**
 * @param {boolean} toggle
 */
export function enableEventLogs(toggle) {
    allowLogs = toggle ?? true;
}

/**
 * Fills the current **active element** with the given `value`. This helper is intended
 * for `<input>` and `<textarea>` elements, with the exception of `"checkbox"` and
 * `"radio"` types, which should be selected using the {@link check} helper.
 *
 * If the target is an editable input, its string `value` will be input one character
 * at a time, each generating its corresponding keyboard event sequence. This behavior
 * can be overriden by passing the `instantly` option, which will instead simulate
 * a `control` + `v` keyboard sequence, resulting in the whole text being pasted.
 *
 * Note that the given value is **appended** to the current value of the element.
 *
 * If the active element is a `<input type="file"/>`, the `value` should be a
 * `File`/list of `File` object(s).
 *
 * @param {InputValue} value
 * @param {FillOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  fill("Hello World"); // Types "Hello World" in the active element
 * @example
 *  fill("Hello World", { instantly: true }); // Pastes "Hello World" in the active element
 * @example
 *  fill(new File(["Hello World"], "hello.txt")); // Uploads a file named "hello.txt" with "Hello World" as content
 */
export async function fill(value, options) {
    const finalizeEvents = setupEvents("fill", options);
    const element = getActiveElement();

    if (!isEditable(element)) {
        throw new HootDomError(`cannot call \`fill()\`: target should be editable`);
    }

    await _fill(element, value, options);

    return finalizeEvents();
}

/**
 * Performs a hover sequence on the given {@link AsyncTarget}.
 *
 * The event sequence is as follows:
 *  - `pointerover`
 *  - [desktop] `mouseover`
 *  - `pointerenter`
 *  - [desktop] `mouseenter`
 *  - `pointermove`
 *  - [desktop] `mousemove`
 *  - [touch] `touchmove`
 *
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  hover("button"); // Hovers the first <button> element
 */
export async function hover(target, options) {
    const finalizeEvents = setupEvents("hover", options);
    const element = queryFirst(await target, options);

    await _hover(element, options);

    return finalizeEvents();
}

/**
 * Performs a key down sequence on the current **active element**.
 *
 * The event sequence is as follows:
 *  - `keydown`
 *
 * Additional actions will be performed depending on the key pressed:
 * - `Tab`: focus next (or previous with `shift`) focusable element;
 * - `c`: copy current selection to clipboard;
 * - `v`: paste current clipboard content to current element;
 * - `Enter`: submit the form if the target is a `<button type="button">` or
 *  a `<form>` element, or trigger a `change` event on the target if it is
 *  an `<input>` element;
 * - `Space`: trigger a `click` event on the target if it is an `<input type="checkbox">`
 *  element.
 *
 * @param {KeyStrokes} keyStrokes
 * @param {KeyboardOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  keyDown(" "); // Space key
 */
export async function keyDown(keyStrokes, options) {
    const finalizeEvents = setupEvents("keyDown", options);
    const eventInits = parseKeyStrokes(keyStrokes, options);
    for (const eventInit of eventInits) {
        await _keyDown(getActiveElement(), eventInit);
    }

    return finalizeEvents();
}

/**
 * Performs a key up sequence on the current **active element**.
 *
 * The event sequence is as follows:
 *  - `keyup`
 *
 * @param {KeyStrokes} keyStrokes
 * @param {KeyboardOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  keyUp("Enter");
 */
export async function keyUp(keyStrokes, options) {
    const finalizeEvents = setupEvents("keyUp", options);
    const eventInits = parseKeyStrokes(keyStrokes, options);
    for (const eventInit of eventInits) {
        await _keyUp(getActiveElement(), eventInit);
    }

    return finalizeEvents();
}

/**
 * Performs a leave sequence on the current **window**.
 *
 * The event sequence is as follows:
 *  - `pointermove`
 *  - [desktop] `mousemove`
 *  - [touch] `touchmove`
 *  - `pointerout`
 *  - [desktop] `mouseout`
 *  - `pointerleave`
 *  - [desktop] `mouseleave`
 *
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  leave("button"); // Moves out of <button>
 */
export async function leave(options) {
    const finalizeEvents = setupEvents("leave", options);

    await _hover(null, options);

    return finalizeEvents();
}

/**
 * Performs a middle-click sequence on the given {@link AsyncTarget}.
 *
 * @see {@link click}
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  middleClick("button"); // Middle-clicks on the first <button> element
 */
export async function middleClick(target, options) {
    const finalizeEvents = setupEvents("middleClick", options);
    const element = queryFirst(await target, options);

    options = { ...options, button: btn.MIDDLE };
    await _implicitHover(element, options);
    await _click(element, options);

    return finalizeEvents();
}

/**
 * Shorthand helper to attach an event listener to the given {@link Target}, and
 * returning a function to remove the listener.
 *
 * @template {EventType} T
 * @param {Target<EventTarget>} target
 * @param {T} type
 * @param {(event: GlobalEventHandlersEventMap[T]) => any} listener
 * @param {boolean | AddEventListenerOptions} [options]
 * @returns {() => void}
 * @example
 *  const off = on("button", "click", onClick);
 *  after(off);
 */
export function on(target, type, listener, options) {
    const targets = isEventTarget(target) ? [target] : queryAll(target);
    if (!targets.length) {
        throw new HootDomError(`expected at least 1 event target, got none`);
    }
    for (const eventTarget of targets) {
        eventTarget.addEventListener(type, listener, options);
    }

    return function off() {
        for (const eventTarget of targets) {
            eventTarget.removeEventListener(type, listener, options);
        }
    };
}

/**
 * Performs a pointer down on the given {@link AsyncTarget}.
 *
 * The event sequence is as follows:
 *  - `pointerdown`
 *  - [desktop] `mousedown`
 *  - [touch] `touchstart`
 *  - [target is not active element] `blur`
 *  - [target is focusable] `focus`
 *
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  pointerDown("button"); // Focuses to the first <button> element
 */
export async function pointerDown(target, options) {
    const finalizeEvents = setupEvents("pointerDown", options);
    const element = queryFirst(await target, options);

    await _implicitHover(element, options);
    await _pointerDown(element, options);

    return finalizeEvents();
}

/**
 * Performs a pointer up on the given {@link AsyncTarget}.
 *
 * The event sequence is as follows:
 * - `pointerup`
 * - [desktop] `mouseup`
 * - [touch] `touchend`
 *
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  pointerUp("body"); // Triggers a pointer up on the <body> element
 */
export async function pointerUp(target, options) {
    const finalizeEvents = setupEvents("pointerUp", options);
    const element = queryFirst(await target, options);

    await _implicitHover(element, options);
    await _pointerUp(element, options);

    return finalizeEvents();
}

/**
 * Performs a keyboard event sequence on the current **active element**.
 *
 * The event sequence is as follows:
 *  - `keydown`
 *  - `keyup`
 *
 * @param {KeyStrokes} keyStrokes
 * @param {KeyboardOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  pointerDown("button[type=submit]"); // Moves focus to <button>
 *  keyDown("Enter"); // Submits the form
 * @example
 *  keyDown("Shift+Tab"); // Focuses previous focusable element
 * @example
 *  keyDown(["ctrl", "v"]); // Pastes current clipboard content
 */
export async function press(keyStrokes, options) {
    const finalizeEvents = setupEvents("press", options);
    const eventInits = parseKeyStrokes(keyStrokes, options);
    const activeElement = getActiveElement();

    for (const eventInit of eventInits) {
        await _keyDown(activeElement, eventInit);
    }
    for (const eventInit of eventInits.reverse()) {
        await _keyUp(activeElement, eventInit);
    }

    return finalizeEvents();
}

/**
 * Performs a resize event sequence on the current **window**.
 *
 * The event sequence is as follows:
 *  - `resize`
 *
 * The target will be resized to the given dimensions, enforced by `!important` style
 * attributes.
 *
 * @param {Dimensions} dimensions
 * @param {EventOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  resize("body", { width: 1000, height: 500 }); // Resizes <body> to 1000x500
 */
export async function resize(dimensions, options) {
    const finalizeEvents = setupEvents("resize", options);
    const [width, height] = parseDimensions(dimensions);

    setDimensions(width, height);

    await dispatch(getWindow(), "resize");

    return finalizeEvents();
}

/**
 * Performs a right-click sequence on the given {@link AsyncTarget}.
 *
 * @see {@link click}
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  rightClick("button"); // Middle-clicks on the first <button> element
 */
export async function rightClick(target, options) {
    const finalizeEvents = setupEvents("rightClick", options);
    const element = queryFirst(await target, options);

    options = { ...options, button: btn.RIGHT };
    await _implicitHover(element, options);
    await _click(element, options);

    return finalizeEvents();
}

/**
 * Performs a scroll event sequence on the given {@link AsyncTarget}.
 *
 * The event sequence is as follows:
 *  - [desktop] `wheel`
 *  - `scroll`
 *
 * @param {AsyncTarget} target
 * @param {Position} position
 * @param {ScrollOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  scroll("body", { y: 0 }); // Scrolls to the top of <body>
 */
export async function scroll(target, position, options) {
    const finalizeEvents = setupEvents("scroll", options);

    const { force, initiator = "wheel", relative } = options || {};
    /** @type {ScrollToOptions} */
    const scrollTopOptions = {};
    const element = queryFirst(await target, { scrollable: true, ...options });
    let [x, y] = parsePosition(position);
    if (relative) {
        x += element.scrollLeft;
        y += element.scrollTop;
    }
    if (!$isNaN(x)) {
        const targetX = force ? x : constrainScrollX(element, x);
        if (targetX !== element.scrollLeft) {
            scrollTopOptions.left = targetX;
        }
    }
    if (!$isNaN(y)) {
        const targetY = force ? y : constrainScrollY(element, y);
        if (targetY !== element.scrollTop) {
            scrollTopOptions.top = targetY;
        }
    }
    const keys = [];
    if (initiator === "keyboard") {
        if (x < element.scrollLeft) {
            keys.push("ArrowRight");
        } else if (x > element.scrollLeft) {
            keys.push("ArrowLeft");
        }
        if (y < element.scrollTop) {
            keys.push("ArrowDown");
        } else if (y > element.scrollTop) {
            keys.push("ArrowUp");
        }
        await Promise.all(keys.map((key) => _keyDown(key)));
    } else if (!hasTouch() && initiator === "wheel") {
        /** @type {WheelEventInit} */
        const wheelEventInit = {};
        if (!$isNaN(x)) {
            wheelEventInit.deltaX = x - element.scrollLeft;
        }
        if (!$isNaN(y)) {
            wheelEventInit.deltaY = y - element.scrollTop;
        }
        await dispatch(element, "wheel", wheelEventInit);
    }
    if (force || $values(scrollTopOptions).length) {
        await dispatchAndIgnore({
            target: element,
            events: ["scroll", "scrollend"],
            callback: (el) => el.scrollTo(scrollTopOptions),
        });
    }
    if (initiator === "keyboard") {
        await Promise.all(keys.map((key) => _keyUp(key)));
    }

    return finalizeEvents();
}

/**
 * Performs a selection event sequence current **active element**. This helper is
 * intended for `<select>` elements only.
 *
 * The event sequence is as follows:
 *  - `change`
 *
 * @param {string | number | (string | number)[]} value
 * @param {SelectOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  click("select[name=country]"); // Focuses <select> element
 *  select("belgium"); // Selects the <option value="belgium"> element
 */
export async function select(value, options) {
    const finalizeEvents = setupEvents("select", options);
    const element = options?.target ? queryFirst(await options.target) : getActiveElement();

    if (!hasTagName(element, "select")) {
        throw new HootDomError(`cannot call \`select()\`: target should be a <select> element`);
    }

    if (options?.target) {
        await _implicitHover(element);
        await _pointerDown(element);
    }
    await _select(element, value);
    if (options?.target) {
        await _pointerUp(element);
    }

    return finalizeEvents();
}

/**
 * Gives the given {@link File} list to the current file input. This helper only
 * works if a file input has been previously interacted with (by clicking on it).
 *
 * @param {MaybeIterable<File>} files
 * @param {EventOptions} [options]
 * @returns {Promise<EventList>}
 */
export async function setInputFiles(files, options) {
    if (!runTime.fileInput) {
        throw new HootDomError(
            `cannot call \`setInputFiles()\`: no file input has been interacted with`
        );
    }

    const finalizeEvents = setupEvents("setInputFiles", options);

    await _fill(runTime.fileInput, files, options);

    runTime.fileInput = null;

    return finalizeEvents();
}

/**
 * Sets the given value to the given "input[type=range]" {@link AsyncTarget}.
 *
 * The event sequence is as follows:
 *  - `pointerdown`
 *  - `input`
 *  - `change`
 *  - `pointerup`
 *
 * @param {AsyncTarget} target
 * @param {number} value
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 */
export async function setInputRange(target, value, options) {
    const finalizeEvents = setupEvents("setInputRange", options);
    const element = queryFirst(await target, options);

    await _implicitHover(element, options);
    await _pointerDown(element, options);
    await _fill(element, value, options);
    await _pointerUp(element, options);

    return finalizeEvents();
}

/**
 * @param {HTMLElement} target
 * @param {{
 *  allowSubmit?: boolean;
 *  allowTrustedEvents?: boolean;
 *  noFileInputRegistration?: boolean;
 * }} [options]
 */
export function setupEventActions(target, options) {
    const eventHandlers = [];
    if (!options?.allowTrustedEvents) {
        eventHandlers.push(...GLOBAL_TRUSTED_EVENTS_CANCELERS);
    }
    if (!options?.noFileInputRegistration) {
        eventHandlers.push(...GLOBAL_FILE_INPUT_REGISTERERS);
    }
    if (!options?.allowSubmit) {
        eventHandlers.push(...GLOBAL_SUBMIT_FORWARDERS);
    }
    for (const [eventType, handler, options] of eventHandlers) {
        window.addEventListener(eventType, handler, options);
    }

    const processedIframes = new WeakSet();
    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (!mutation.addedNodes) {
                continue;
            }
            for (const iframe of target.getElementsByTagName("iframe")) {
                if (processedIframes.has(iframe)) {
                    continue;
                }
                processedIframes.add(iframe);
                for (const [eventType, handler, options] of eventHandlers) {
                    iframe.contentWindow.addEventListener(eventType, handler, options);
                }
            }
        }
    });

    observer.observe(target, { childList: true, subtree: true });

    return function cleanupEventActions() {
        observer.disconnect();

        if (runTime.pointerDownTimeout) {
            globalThis.clearTimeout(runTime.pointerDownTimeout);
        }

        removeChangeTargetListeners();

        for (const [eventType, handler, options] of eventHandlers) {
            window.removeEventListener(eventType, handler, options);
        }

        // Runtime global variables
        $assign(runTime, getDefaultRunTimeValue());
    };
}

/**
 * Ensures that the given {@link AsyncTarget} is unchecked.
 *
 * If it is checked, a click is triggered on the input.
 * If the input is still checked after the click, an error is thrown.
 *
 * @see {@link click}
 * @param {AsyncTarget} target
 * @param {PointerOptions} [options]
 * @returns {Promise<EventList>}
 * @example
 *  uncheck("input[type=checkbox]"); // Unchecks the first <input> checkbox element
 */
export async function uncheck(target, options) {
    const finalizeEvents = setupEvents("uncheck", options);
    const element = queryFirst(await target, options);
    if (!isCheckable(element)) {
        throw new HootDomError(
            `cannot call \`uncheck()\`: target should be a checkbox or radio input`
        );
    }

    const checkTarget = getTag(element) === "label" ? element.control : element;
    if (checkTarget.checked) {
        await _implicitHover(element, options);
        await _click(element, options);

        if (checkTarget.checked) {
            throw new HootDomError(
                `error when calling \`uncheck()\`: target is still checked after interaction`
            );
        }
    }

    return finalizeEvents();
}

/**
 * Triggers a "beforeunload" event the current **window**.
 *
 * @param {EventOptions} [options]
 * @returns {Promise<EventList>}
 */
export async function unload(options) {
    const finalizeEvents = setupEvents("unload", options);

    await dispatch(getWindow(), "beforeunload");

    return finalizeEvents();
}

/** @extends {Array<Event>} */
export class EventList extends Array {
    constructor(...args) {
        super(...args.flat());
    }

    /**
     * @param {EventListPredicate} predicate
     */
    get(predicate) {
        return this.getAll(predicate)[0] || null;
    }

    /**
     * @param {EventListPredicate} predicate
     */
    getAll(predicate) {
        if (typeof predicate !== "function") {
            const type = predicate;
            predicate = (ev) => ev.type === type;
        }
        return this.filter(predicate);
    }
}
