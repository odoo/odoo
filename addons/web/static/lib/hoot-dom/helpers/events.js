/** @odoo-module */

import { HootDomError, getTag, isFirefox, isIterable } from "../hoot_dom_utils";
import {
    getActiveElement,
    getDocument,
    getNextFocusableElement,
    getNodeValue,
    getPreviousFocusableElement,
    getNodeRect,
    getWindow,
    isCheckable,
    isEditable,
    isEventTarget,
    isNode,
    isNodeFocusable,
    parseDimensions,
    parsePosition,
    queryAll,
    queryOne,
    setDimensions,
    toSelector,
} from "./dom";

/**
 * @typedef {"blur" | "enter" | "tab" | false} ConfirmAction
 *
 * @typedef {{
 *  cancel: () => Event[];
 *  drop: (to?: Target, options?: PointerOptions) => Event[];
 *  moveTo: (to?: Target, options?: PointerOptions) => DragHelpers;
 * }} DragHelpers
 *
 * @typedef {import("./dom").Position} Position
 *
 * @typedef {import("./dom").Dimensions} Dimensions
 *
 * @typedef {keyof HTMLElementEventMap | keyof WindowEventMap} EventType
 *
 * @typedef {{
 *  confirm?: ConfirmAction;
 *  composition?: boolean;
 *  instantly?: boolean;
 * }} FillOptions
 *
 * @typedef {string | number | MaybeIterable<File>} InputValue
 *
 * @typedef {string | string[]} KeyStrokes
 *
 * @typedef {QueryOptions & {
 *  button?: number,
 *  position?: Side | `${Side}-${Side}` | Position;
 *  relative?: boolean;
 * }} PointerOptions
 *
 * @typedef {import("./dom").QueryOptions} QueryOptions
 *
 * @typedef {{ target: Target }} SelectOptions
 *
 * @typedef {"bottom" | "left" | "right" | "top"} Side
 *
 * @typedef {import("./dom").Target} Target
 */

/**
 * @template T
 * @typedef {T | Iterable<T>} MaybeIterable
 */

//-----------------------------------------------------------------------------
// Global
//-----------------------------------------------------------------------------

const {
    console: { dir: $dir, groupCollapsed: $groupCollapsed, groupEnd: $groupEnd, log: $log },
    DataTransfer,
    document,
    Math: { ceil: $ceil },
    Object: { assign: $assign, values: $values },
    String,
    Touch,
    TypeError,
} = globalThis;
/** @type {Document["createRange"]} */
const $createRange = document.createRange.bind(document);
/** @type {Document["hasFocus"]} */
const $hasFocus = document.hasFocus.bind(document);

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @param {EventTarget} target
 * @param {EventType[]} eventSequence
 * @param {EventInit} eventInit
 */
const dispatchEventSequence = (target, eventSequence, eventInit) => {
    for (const eventType of eventSequence) {
        if (!eventType) {
            continue;
        }
        const event = dispatch(target, eventType, eventInit);
        if (isPrevented(event)) {
            return true;
        }
    }
    return false;
};

/**
 * @param {Iterable<Event>} events
 * @param {EventType} eventType
 * @param {EventInit} eventInit
 */
const dispatchRelatedEvents = (events, eventType, eventInit) => {
    for (const event of events) {
        if (!event.target || isPrevented(event)) {
            break;
        }
        dispatch(event.target, eventType, eventInit);
    }
};

/**
 * @template T
 * @param {MaybeIterable<T>} value
 * @returns {T[]}
 */
const ensureArray = (value) => (isIterable(value) ? [...value] : [value]);

const getDefaultRunTimeValue = () => ({
    // Composition
    isComposing: false,

    // Drag & drop
    canStartDrag: false,
    isDragging: false,
    lastDragOverCancelled: false,

    // Pointer
    currentClickCount: 0,
    currentPointerDownTarget: null,
    currentPointerDownTimeout: 0,
    currentPointerTarget: null,
    currentPosition: {},
    previousPointerDownTarget: null,
    previousPointerTarget: null,

    // File
    currentFileInput: null,
});

const getDefaultSpecialKeysValue = () => ({
    altKey: false,
    ctrlKey: false,
    metaKey: false,
    shiftKey: false,
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
 * @returns {[T, (attrs: EventInit) => EventInit]}
 */
const getEventConstructor = (eventType) => {
    switch (eventType) {
        // Mouse events
        case "auxclick":
        case "contextmenu":
        case "dblclick":
        case "mousedown":
        case "mouseup":
        case "mousemove":
        case "mouseover":
        case "mouseout":
            return [MouseEvent, mapBubblingPointerEvent];
        case "mouseenter":
        case "mouseleave":
            return [MouseEvent, mapNonBubblingPointerEvent];

        // Pointer events
        case "click":
        case "pointerdown":
        case "pointerup":
        case "pointermove":
        case "pointerover":
        case "pointerout":
            return [PointerEvent, mapBubblingPointerEvent];
        case "pointerenter":
        case "pointerleave":
        case "pointercancel":
            return [PointerEvent, mapNonBubblingPointerEvent];

        // Focus events
        case "focusin":
            return [FocusEvent, mapBubblingEvent];
        case "focus":
        case "blur":
            return [FocusEvent, mapNonBubblingEvent];

        // Clipboard events
        case "cut":
        case "copy":
        case "paste":
            return [ClipboardEvent, mapBubblingEvent];

        // Keyboard events
        case "keydown":
        case "keyup":
            return [KeyboardEvent, mapKeyboardEvent];

        // Drag events
        case "drag":
        case "dragend":
        case "dragenter":
        case "dragstart":
        case "dragleave":
        case "dragover":
        case "drop":
            return [DragEvent, mapBubblingEvent];

        // Input events
        case "beforeinput":
            return [InputEvent, mapCancelableInputEvent];
        case "input":
            return [InputEvent, mapInputEvent];

        // Composition events
        case "compositionstart":
        case "compositionend":
            return [CompositionEvent, mapBubblingEvent];

        // Touch events
        case "touchstart":
        case "touchend":
        case "touchmove":
            return [TouchEvent, mapCancelableTouchEvent];
        case "touchcancel":
            return [TouchEvent, mapNonCancelableTouchEvent];

        // Resize events
        case "resize":
            return [Event, mapNonBubblingEvent];

        // Submit events
        case "submit":
            return [SubmitEvent, mapBubblingCancelableEvent];

        // Wheel events
        case "wheel":
            return [WheelEvent, mapWheelEvent];

        case "beforeunload":
            // BeforeUnloadEvent cannot be constructed.
            return [Event, mapNonBubblingCancelableEvent];

        case "unload":
            return [Event, mapNonBubblingEvent];

        // Default: base Event constructor
        default:
            return [Event, mapBubblingEvent];
    }
};

/**
 * @param {Target} target
 * @param {QueryOptions} options
 * @returns {EventTarget}
 */
const getFirstTarget = (target, options) =>
    isEventTarget(target) ? target : queryAll(target, options)[0];

/**
 * @param {HTMLElement} element
 * @param {PointerOptions} [options]
 */
const getPosition = (element, options) => {
    const { position, relative } = options || {};
    const isString = typeof position === "string";
    const [posX, posY] = parsePosition(position);

    if (!isString && !relative && !Number.isNaN(posX) && !Number.isNaN(posY)) {
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
        if (Number.isNaN(posX)) {
            clientX += width / 2;
        } else {
            if (relative) {
                clientX += posX || 0;
            } else {
                clientX = posX || 0;
            }
        }

        // Y position
        if (Number.isNaN(posY)) {
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
    Number.isInteger(target.selectionStart) &&
    Number.isInteger(target.selectionEnd) &&
    [target.selectionStart, target.selectionEnd].join(",");

/**
 * @param {Node} node
 * @param  {...string} tagNames
 */
const hasTagName = (node, ...tagNames) => tagNames.includes(getTag(node));

const hasTouch = () =>
    globalThis.ontouchstart !== undefined || globalThis.matchMedia("(pointer:coarse)").matches;

/**
 * @param {unknown} value
 */
const isNil = (value) => value === null || value === undefined;

/**
 * @param {Event} event
 */
const isPrevented = (event) => event && event.defaultPrevented;

/**
 * @param {string} actionName
 */
const logEvents = (actionName) => {
    const events = currentEvents;
    currentEvents = [];
    if (!allowLogs) {
        return events;
    }
    const groupName = [`${actionName}: dispatched`, events.length, `events`];
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
        if (isNode(event.target)) {
            const targetParts = toSelector(event.target, { object: true });
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
        $log(event.target);
        $groupEnd();
    }
    $groupEnd();
    return events;
};

/**
 * @param {KeyStrokes} keyStrokes
 * @param {KeyboardEventInit} [options]
 * @returns {KeyboardEventInit}
 */
const parseKeyStrokes = (keyStrokes, options) =>
    (isIterable(keyStrokes) ? [...keyStrokes] : [keyStrokes])
        .flatMap((keyStroke) => keyStroke.split(/\s*[,+]\s*/))
        .map((key) => {
            const lower = key.toLowerCase();
            return {
                ...options,
                key: lower.length === 1 ? key : KEY_ALIASES[lower] || key,
            };
        });

/**
 * @param {Event} ev
 */
const registerFileInput = ({ target }) => {
    if (getTag(target) === "input" && target.type === "file") {
        runTime.currentFileInput = target;
    } else {
        runTime.currentFileInput = null;
    }
};

/**
 * @param {EventTarget} target
 * @param {string} initialValue
 * @param {ConfirmAction} confirmAction
 */
const registerForChange = (target, initialValue, confirmAction) => {
    const triggerChange = () => {
        removeChangeTargetListeners();

        if (target.value !== initialValue) {
            afterNextDispatch = () => dispatch(target, "change");
        }
    };

    confirmAction &&= confirmAction.toLowerCase();
    if (confirmAction === "enter") {
        if (getTag(target) === "input") {
            changeTargetListeners.push(
                on(
                    target,
                    "keydown",
                    (ev) => !isPrevented(ev) && ev.key === "Enter" && triggerChange()
                )
            );
        } else {
            throw new HootDomError(`"enter" confirm action is only supported on <input/> elements`);
        }
    }

    changeTargetListeners.push(
        on(target, "blur", triggerChange),
        on(target, "change", removeChangeTargetListeners)
    );

    switch (confirmAction) {
        case "blur": {
            _click(getDocument(target).body, {
                position: { x: 0, y: 0 },
            });
            break;
        }
        case "enter": {
            _press(target, { key: "Enter" });
            break;
        }
        case "tab": {
            _press(target, { key: "Tab" });
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
        case "Alt":
            specialKeys.altKey = toggle;
            break;
        case "Control":
            specialKeys.ctrlKey = toggle;
            break;
        case "Meta":
            specialKeys.metaKey = toggle;
            break;
        case "Shift":
            specialKeys.shiftKey = toggle;
            break;
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
    if (runTime.currentPointerDownTarget) {
        runTime.previousPointerDownTarget = runTime.currentPointerDownTarget;
    }
    runTime.currentPointerDownTarget = target;
    runTime.canStartDrag = false;
};

/**
 * @param {HTMLElement | null} target
 * @param {PointerOptions} [options]
 */
const setPointerTarget = (target, options) => {
    runTime.previousPointerTarget = runTime.currentPointerTarget;
    runTime.currentPointerTarget = target;

    if (runTime.currentPointerTarget !== runTime.previousPointerTarget && runTime.canStartDrag) {
        /**
         * Special action: drag start
         *  On: unprevented 'pointerdown' on a draggable element (DESKTOP ONLY)
         *  Do: triggers a 'dragstart' event
         */
        const dragStartEvent = dispatch(runTime.previousPointerTarget, "dragstart");

        runTime.isDragging = !isPrevented(dragStartEvent);
        runTime.canStartDrag = false;
    }

    runTime.currentPosition = target && getPosition(target, options);
};

/**
 * @param {number} x
 * @param {number} y
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
 * @param {PointerEventInit} eventInit
 */
const triggerClick = (target, pointerInit) => {
    const clickEvent = dispatch(target, "click", pointerInit);
    if (isPrevented(clickEvent)) {
        return;
    }
    if (isFirefox()) {
        // Thanks Firefox
        switch (getTag(target)) {
            case "input": {
                if (isCheckable(target)) {
                    /**
                     * @firefox
                     * Special action: input 'Click'
                     *  On: unprevented 'click' on an <input type="checkbox|radio"/>
                     *  Do: triggers a 'change' event on the input
                     */
                    target.checked = target.type === "radio" ? true : !target.checked;
                    dispatch(target, "change");
                }
                break;
            }
            case "label": {
                /**
                 * @firefox
                 * Special action: label 'Click'
                 *  On: unprevented 'click' on a <label/>
                 *  Do: triggers a 'click' event on the first <input/> descendant
                 */
                target = target.control;
                if (target) {
                    triggerClick(target, pointerInit);
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
                    dispatch(parent, "change");
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
const triggerDrag = (target, eventInit) => {
    dispatch(target, "drag", eventInit);
    // Only "dragover" being prevented is taken into account for "drop" events
    const dragOverEvent = dispatch(target, "dragover", eventInit);
    runTime.lastDragOverCancelled = isPrevented(dragOverEvent);
};

/**
 * @param {EventTarget} target
 */
const triggerFocus = (target) => {
    const previous = getActiveElement(target);
    if (previous === target) {
        return;
    }
    if (previous !== target.ownerDocument.body) {
        // If document is focused, this will trigger a trusted "blur" event
        previous.blur();
        if (!$hasFocus()) {
            // When document is not focused: manually trigger a "blur" event
            dispatch(previous, "blur", { relatedTarget: target });
        }
    }
    if (isNodeFocusable(target)) {
        const previousSelection = getStringSelection(target);

        // If document is focused, this will trigger a trusted "focus" event
        target.focus();
        if (!$hasFocus()) {
            // When document is not focused: manually trigger a "focus" event
            dispatch(target, "focus", { relatedTarget: previous });
        }

        if (previousSelection && previousSelection === getStringSelection(target)) {
            target.selectionStart = target.selectionEnd = target.value.length;
        }
    }
};

/**
 * @param {HTMLInputElement | HTMLTextAreaElement} target
 */
const deleteSelection = (target) => {
    const { selectionStart, selectionEnd, value } = target;
    return value.slice(0, selectionStart) + value.slice(selectionEnd);
};

/**
 * @param {EventTarget} target
 * @param {FillOptions} options
 */
const _clear = (target, options) => {
    // Inputs and text areas
    const initialValue = target.value;

    // Simulates 2 key presses:
    // - Control + A: selects all the text
    // - Backspace: deletes the text
    fullClear = true;
    _press(target, { ctrlKey: true, key: "a" });
    _press(target, { key: "Backspace" });
    fullClear = false;

    registerForChange(target, initialValue, options?.confirm);
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} [option]
 */
const _click = (target, options) => {
    _pointerDown(target, options);
    _pointerUp(target, options);
};

/**
 * @param {EventTarget} target
 * @param {InputValue} value
 * @param {FillOptions} [options]
 */
const _fill = (target, value, options) => {
    const initialValue = target.value;

    if (getTag(target) === "input") {
        switch (target.type) {
            case "color": {
                target.value = String(value);
                dispatch(target, "input");
                dispatch(target, "change");
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

                dispatch(target, "change");
                return;
            }
            case "range": {
                const numberValue = Number(value);
                if (Number.isNaN(numberValue)) {
                    throw new TypeError(`input[type="range"] only accept 'number' values`);
                }

                target.value = String(numberValue);
                dispatch(target, "input");
                dispatch(target, "change");
                return;
            }
        }
    }

    if (options?.instantly) {
        // Simulates filling the clipboard with the value (can be from external source)
        globalThis.navigator.clipboard.writeTextSync(value);
        _press(target, { ctrlKey: true, key: "v" });
    } else {
        if (options?.composition) {
            runTime.isComposing = true;
            // Simulates the start of a composition
            dispatch(target, "compositionstart");
        }
        for (const char of String(value)) {
            const key = char.toLowerCase();
            _press(target, { key, shiftKey: key !== char });
        }
        if (options?.composition) {
            runTime.isComposing = false;
            // Simulates the end of a composition
            dispatch(target, "compositionend");
        }
    }

    registerForChange(target, initialValue, options?.confirm);
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} options
 */
const _hover = (target, options) => {
    const isDifferentTarget = target !== runTime.currentPointerTarget;
    const previousPosition = runTime.currentPosition;

    setPointerTarget(target, options);

    const { previousPointerTarget: previous, currentPointerTarget: current } = runTime;
    if (isDifferentTarget && previous && (!current || !previous.contains(current))) {
        // Leaves previous target
        const leaveEventInit = {
            ...previousPosition,
            relatedTarget: current,
        };

        if (runTime.isDragging) {
            // If dragging, only drag events are triggered
            triggerDrag(previous, leaveEventInit);
            dispatch(previous, "dragleave", leaveEventInit);
        } else {
            // Regular case: pointer events are triggered
            dispatchEventSequence(
                previous,
                ["pointermove", hasTouch() ? "touchmove" : "mousemove"],
                leaveEventInit
            );
            dispatchEventSequence(
                previous,
                ["pointerout", !hasTouch() && "mouseout"],
                leaveEventInit
            );
            const leaveEvents = getDifferentParents(current, previous).map((element) =>
                dispatch(element, "pointerleave", leaveEventInit)
            );
            if (!hasTouch()) {
                dispatchRelatedEvents(leaveEvents, "mouseleave", leaveEventInit);
            }
        }
    }

    if (current) {
        const enterEventInit = {
            ...runTime.currentPosition,
            relatedTarget: previous,
        };
        if (runTime.isDragging) {
            // If dragging, only drag events are triggered
            if (isDifferentTarget) {
                dispatch(target, "dragenter", enterEventInit);
            }
            triggerDrag(target, enterEventInit);
        } else {
            // Regular case: pointer events are triggered
            if (isDifferentTarget) {
                dispatchEventSequence(
                    target,
                    ["pointerover", !hasTouch() && "mouseover"],
                    enterEventInit
                );
                const enterEvents = getDifferentParents(previous, current).map((element) =>
                    dispatch(element, "pointerenter", enterEventInit)
                );
                if (!hasTouch()) {
                    dispatchRelatedEvents(enterEvents, "mouseenter", enterEventInit);
                }
            }
            dispatchEventSequence(
                target,
                ["pointermove", hasTouch() ? "touchmove" : "mousemove"],
                enterEventInit
            );
        }
    }
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} options
 */
const _implicitHover = (target, options) => {
    if (runTime.currentPointerTarget !== target) {
        _hover(target, options);
    }
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _keyDown = (target, eventInit) => {
    registerSpecialKey(eventInit, true);

    const keyDownEvent = dispatch(target, "keydown", eventInit);

    if (isPrevented(keyDownEvent)) {
        return;
    }

    const { ctrlKey, key, shiftKey } = keyDownEvent;
    let inputData = null;
    let inputType = null;
    let nextValue = target.value;

    if (isEditable(target)) {
        switch (key) {
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
                    nextValue += "\n";
                    inputType = "insertLineBreak";
                }
                break;
            }
            default: {
                if (key.length === 1 && !ctrlKey) {
                    // Character coming from the keystroke
                    // ! TODO: Doesn't work with non-roman locales
                    const { selectionStart, selectionEnd, value } = target;
                    inputData = shiftKey ? key.toUpperCase() : key.toLowerCase();
                    // Insert character in target value
                    if (isNil(selectionStart) && isNil(selectionEnd)) {
                        nextValue += inputData;
                    } else {
                        nextValue =
                            value.slice(0, selectionStart) + inputData + value.slice(selectionEnd);
                    }
                    inputType = runTime.isComposing ? "insertCompositionText" : "insertText";
                }
            }
        }
    }

    switch (key) {
        case "a": {
            if (ctrlKey) {
                // Select all
                if (isEditable(target)) {
                    dispatch(target, "select");
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
                globalThis.navigator.clipboard.writeTextSync(text);

                dispatch(target, "copy", {
                    clipboardData: eventInit.dataTransfer || new DataTransfer(),
                });
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
            const next = shiftKey ? getPreviousFocusableElement() : getNextFocusableElement();
            if (next) {
                triggerFocus(next);
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
                // Set target value (synchonously)
                const value = globalThis.navigator.clipboard.readTextSync();
                nextValue = value;

                inputType = "insertFromPaste";

                dispatch(target, "paste", {
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
                globalThis.navigator.clipboard.writeTextSync(text);

                nextValue = deleteSelection(target);
                inputType = "deleteByCut";

                dispatch(target, "cut", {
                    clipboardData: eventInit.dataTransfer || new DataTransfer(),
                });
            }
            break;
        }
    }

    if (target.value !== nextValue) {
        target.value = nextValue;
        dispatchEventSequence(target, ["beforeinput", "input"], {
            data: inputData,
            inputType,
        });
    }
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _keyUp = (target, eventInit) => {
    dispatch(target, "keyup", eventInit);

    registerSpecialKey(eventInit, false);

    if (eventInit.key === "Enter") {
        let parentForm;
        if (getTag(target) === "button" && target.type === "button") {
            /**
             * Special action: button 'Enter'
             *  On: unprevented 'Enter' keydown on a <button type="button"/>
             *  Do: triggers a 'click' event on the button
             */
            triggerClick(target, { button: 0 });
        } else if ((parentForm = target.closest("form"))) {
            /**
             * Special action: form 'Enter'
             *  On: unprevented 'Enter' keydown on any element that
             *      is not a <button type="button"/> in a form element
             *  Do: triggers a 'submit' event on the form
             */
            dispatch(parentForm, "submit");
        }
    }
    if (eventInit.key === " " && getTag(target) === "input" && target.type === "checkbox") {
        /**
         * Special action: input[type=checkbox] 'Space'
         *  On: unprevented ' ' keydown on an <input type="checkbox"/>
         *  Do: triggers a 'click' event on the input
         */
        triggerClick(target, { button: 0 });
    }
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} options
 */
const _pointerDown = (target, options) => {
    setPointerDownTarget(target);

    const eventInit = {
        ...runTime.currentPosition,
        button: options?.button || 0,
    };

    if (runTime.currentPointerDownTarget !== runTime.previousPointerDownTarget) {
        runTime.currentClickCount = 0;
    }

    const prevented = dispatchEventSequence(
        target,
        ["pointerdown", hasTouch() ? "touchstart" : "mousedown"],
        eventInit
    );
    if (prevented) {
        return;
    }

    // Focus the element (if focusable)
    triggerFocus(target);

    if (eventInit.button === 0 && !hasTouch() && runTime.currentPointerDownTarget.draggable) {
        runTime.canStartDrag = true;
    } else if (eventInit.button === 2) {
        /**
         * Special action: context menu
         *  On: unprevented 'pointerdown' with right click and its related
         *      event on an element
         *  Do: triggers a 'contextmenu' event
         */
        dispatch(target, "contextmenu", eventInit);
    }
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} options
 */
const _pointerUp = (target, options) => {
    const eventInit = {
        ...runTime.currentPosition,
        button: options?.button || 0,
    };

    if (runTime.isDragging) {
        // If dragging, only drag events are triggered
        runTime.isDragging = false;
        if (runTime.lastDragOverCancelled) {
            /**
             * Special action: drop
             * - On: prevented 'dragover'
             * - Do: triggers a 'drop' event on the target
             */
            dispatch(target, "drop", eventInit);
        }

        dispatch(target, "dragend", eventInit);
        return;
    }

    const prevented = dispatchEventSequence(
        target,
        ["pointerup", hasTouch() ? "touchend" : "mouseup"],
        eventInit
    );

    if (!prevented) {
        if (target === runTime.currentPointerDownTarget) {
            triggerClick(target, eventInit);
            runTime.currentClickCount++;
            if (!hasTouch() && runTime.currentClickCount % 2 === 0) {
                dispatch(target, "dblclick", eventInit);
            }
        }
    }

    setPointerDownTarget(null);
    if (runTime.currentPointerDownTimeout) {
        globalThis.clearTimeout(runTime.currentPointerDownTimeout);
    }
    runTime.currentPointerDownTimeout = globalThis.setTimeout(() => {
        // Use `globalThis.setTimeout` to potentially make use of the mock timeouts
        // since the events run in the same temporal context as the tests
        runTime.currentClickCount = 0;
        runTime.currentPointerDownTimeout = 0;
    }, DOUBLE_CLICK_DELAY);
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _press = (target, eventInit) => {
    _keyDown(target, eventInit);
    _keyUp(target, eventInit);
};

/**
 * @param {EventTarget} target
 * @param {string | number | (string | number)[]} value
 */
const _select = (target, value) => {
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
    dispatch(target, "change");
};

const DEPRECATED_EVENT_PROPERTIES = {
    keyCode: "key",
    which: "key",
};
const DEPRECATED_EVENTS = {
    keypress: "keydown",
    mousewheel: "wheel",
};
const DOUBLE_CLICK_DELAY = 500;
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
/** @type {(() => void) | null} */
let afterNextDispatch = null;
let allowLogs = false;
/** @type {Event[]} */
let currentEvents = [];
let fullClear = false;

// Keyboard global variables
const changeTargetListeners = [];
const specialKeys = getDefaultSpecialKeysValue();

// Other global variables
const runTime = getDefaultRunTimeValue();

//-----------------------------------------------------------------------------
// Event init attributes mappers
//-----------------------------------------------------------------------------

// Generic mappers
// ---------------

/**
 * - bubbles
 * - can be canceled
 * @param {EventInit} [eventInit]
 */
const mapBubblingCancelableEvent = (eventInit) => ({
    ...mapBubblingEvent(eventInit),
    cancelable: true,
});

/**
 * - bubbles
 * - cannot be canceled
 * @param {EventInit} [eventInit]
 */
const mapBubblingEvent = (eventInit) => ({
    composed: true,
    ...eventInit,
    bubbles: true,
});

/**
 * - does not bubble
 * - can be canceled
 * @param {EventInit} [eventInit]
 */
const mapNonBubblingCancelableEvent = (eventInit) => ({
    ...mapNonBubblingEvent(eventInit),
    cancelable: true,
});

/**
 * - does not bubble
 * - cannot be canceled
 * @param {EventInit} [eventInit]
 */
const mapNonBubblingEvent = (eventInit) => ({
    composed: true,
    ...eventInit,
});

// Pointer & wheel event mappers
// -----------------------------

/**
 * @param {PointerEventInit} [eventInit]
 */
const mapBubblingPointerEvent = (eventInit) => ({
    clientX: eventInit?.clientX ?? eventInit?.pageX ?? 0,
    clientY: eventInit?.clientY ?? eventInit?.pageY ?? 0,
    view: getWindow(),
    ...specialKeys,
    ...mapBubblingCancelableEvent(eventInit),
});

/**
 * @param {PointerEventInit} [eventInit]
 */
const mapNonBubblingPointerEvent = (eventInit) => ({
    ...specialKeys,
    ...mapBubblingPointerEvent(eventInit),
    bubbles: false,
    cancelable: false,
});

/**
 * @param {WheelEventInit} [eventInit]
 */
const mapWheelEvent = (eventInit) => ({
    ...specialKeys,
    ...mapBubblingEvent(eventInit),
});

// Touch event mappers
// -------------------

/**
 * @param {TouchEventInit} [eventInit]
 */
const mapCancelableTouchEvent = (eventInit) => {
    const touches = eventInit?.touches ||
        eventInit?.changedTouches || [new Touch({ identifier: 0, ...eventInit })];
    return {
        view: getWindow(),
        ...mapBubblingCancelableEvent(eventInit),
        changedTouches: eventInit?.changedTouches || touches,
        touches: eventInit?.touches || touches,
    };
};

/**
 * @param {TouchEventInit} [eventInit]
 */
const mapNonCancelableTouchEvent = (eventInit) => ({
    ...mapCancelableTouchEvent(eventInit),
    cancelable: false,
});

// Keyboard & input event mappers
// ------------------------------

/**
 * @param {InputEventInit} [eventInit]
 */
const mapCancelableInputEvent = (eventInit) => ({
    ...mapInputEvent(eventInit),
    cancelable: true,
});

/**
 * @param {InputEventInit} [eventInit]
 */
const mapInputEvent = (eventInit) => ({
    data: null,
    isComposing: Boolean(runTime.isComposing),
    view: getWindow(),
    ...mapBubblingEvent(eventInit),
});

/**
 * @param {TouchEventInit} [eventInit]
 */
const mapKeyboardEvent = (eventInit) => ({
    ...specialKeys,
    isComposing: Boolean(runTime.isComposing),
    view: getWindow(),
    ...mapBubblingCancelableEvent(eventInit),
});

//-----------------------------------------------------------------------------
// Exports
//-----------------------------------------------------------------------------

/**
 * Ensures that the given {@link Target} is checked.
 *
 * If it is not checked, a click is triggered on the input.
 * If the input is still not checked after the click, an error is thrown.
 *
 * @see {@link click}
 * @param {Target} target
 * @param {PointerOptions} [options]
 * @returns {Event[]}
 * @example
 *  check("input[type=checkbox]"); // Checks the first <input> checkbox element
 */
export function check(target, options) {
    const element = getFirstTarget(target, options);
    if (!isCheckable(element)) {
        throw new HootDomError(
            `cannot call \`check()\`: target should be a checkbox or radio input`
        );
    }

    const checkTarget = getTag(element) === "label" ? element.control : element;
    if (!checkTarget.checked) {
        _implicitHover(element, options);
        _click(element, options);

        if (!checkTarget.checked) {
            throw new HootDomError(
                `error when calling \`check()\`: target is not checked after interaction`
            );
        }
    }

    return logEvents("check");
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
 * @returns {Event[]}
 * @example
 *  clear(); // Clears the value of the current active element
 */
export function clear(options) {
    const element = getActiveElement();

    if (!hasTagName(element, "select") && !isEditable(element)) {
        throw new HootDomError(
            `cannot call \`clear()\`: target should be editable or a <select> element`
        );
    }

    if (isEditable(element)) {
        _clear(element, options);
    } else {
        // Selects
        _select(element, "");
    }

    return logEvents("clear");
}

/**
 * Performs a click sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
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
 * @param {Target} target
 * @param {PointerOptions} [options]
 * @returns {Event[]}
 * @example
 *  click("button"); // Clicks on the first <button> element
 */
export function click(target, options) {
    const element = getFirstTarget(target, options);

    _implicitHover(element, options);
    _click(element, options);

    return logEvents("click");
}

/**
 * Performs two click sequences on the given {@link Target}.
 *
 * @see {@link click}
 * @param {Target} target
 * @param {PointerOptions} [options]
 * @returns {Event[]}
 * @example
 *  dblclick("button"); // Double-clicks on the first <button> element
 */
export function dblclick(target, options) {
    const element = getFirstTarget(target, options);

    _implicitHover(element, options);
    _click(element, options);
    _click(element, options);

    return logEvents("dblclick");
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
 * @param {EventTarget} target
 * @param {T} type
 * @param {EventInit} [eventInit]
 * @returns {GlobalEventHandlersEventMap[T]}
 * @example
 *  dispatch(document.querySelector("input"), "paste"); // Dispatches a "paste" event on the given <input>
 */
export function dispatch(target, type, eventInit) {
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
    if (eventInit && typeof eventInit === "object") {
        for (const key in eventInit) {
            if (key in DEPRECATED_EVENT_PROPERTIES) {
                throw new HootDomError(
                    `cannot dispatch "${type}" event: property "${key}" is deprecated, use "${DEPRECATED_EVENT_PROPERTIES[key]}" instead`
                );
            }
        }
    }

    const [Constructor, processParams] = getEventConstructor(type);
    const event = new Constructor(type, processParams({ ...eventInit, target }));

    target.dispatchEvent(event);
    currentEvents.push(event);

    if (afterNextDispatch) {
        const callback = afterNextDispatch;
        afterNextDispatch = null;
        callback();
    }

    return event;
}

/**
 * Starts a drag sequence on the given {@link Target}.
 *
 * Returns a set of helper functions to direct the sequence:
 * - `moveTo`: moves the pointer to the given target;
 * - `drop`: drops the dragged element on the given target (if any);
 * - `cancel`: cancels the drag sequence.
 *
 * @param {Target} target
 * @param {PointerOptions} [options]
 * @returns {DragHelpers}
 * @example
 *  drag(".card:first").drop(".card:last"); // Drags the first card onto the last one
 * @example
 *  drag(".card:first").moveTo(".card:last").drop(); // Same as above
 * @example
 *  const { cancel, moveTo } = drag(".card:first"); // Starts the drag sequence
 *  moveTo(".card:eq(3)"); // Moves the dragged card to the 4th card
 *  cancel(); // Cancels the drag sequence
 */
export function drag(target, options) {
    /**
     * @template T
     * @param {T} fn
     * @param {boolean} endDrag
     * @returns {T}
     */
    const expectIsDragging = (fn, endDrag) => {
        return {
            [fn.name](...args) {
                if (dragEndReason) {
                    throw new HootDomError(
                        `cannot execute drag helper \`${fn.name}\`: drag sequence has been ended by \`${dragEndReason}\``
                    );
                }
                const result = fn(...args);
                if (endDrag) {
                    dragEndReason = fn.name;
                }
                return result;
            },
        }[fn.name];
    };

    const cancel = expectIsDragging(
        /** @type {DragHelpers["cancel"]} */
        function cancel() {
            _press(getDocument().body, { key: "Escape" });

            return logEvents("drag & drop (canceled)");
        },
        true
    );

    const drop = expectIsDragging(
        /** @type {DragHelpers["drop"]} */
        function drop(to, options) {
            if (to) {
                _hover(queryOne(to), options);
            }

            _pointerUp(runTime.currentPointerTarget, options);

            return logEvents("drag & drop");
        },
        true
    );

    const moveTo = expectIsDragging(
        /** @type {DragHelpers["moveTo"]} */
        function moveTo(to, options) {
            _hover(queryOne(to), options);

            return dragHelpers;
        },
        false
    );

    const dragHelpers = { cancel, drop, moveTo };
    const element = getFirstTarget(target);

    let dragEndReason = null;

    // Pointer down on main target
    _implicitHover(element, options);
    _pointerDown(element, options);

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
 * @returns {Event[]}
 * @example
 *  fill("foo"); // Types "foo" in the active element
 *  edit("Hello World"); // Replaces "foo" by "Hello World"
 */
export function edit(value, options) {
    const element = getActiveElement();
    if (!isEditable(element)) {
        throw new HootDomError(`cannot call \`edit()\`: target should be editable`);
    }

    if (getNodeValue(element)) {
        _clear(element);
    }
    _fill(element, value, options);

    return logEvents("edit");
}

/**
 * @param {boolean} toggle
 */
export function enableEventLogs(toggle) {
    allowLogs = toggle ?? true;
}

/**
 * Fills the current active element with the given `value`. This helper is intended
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
 * @returns {Event[]}
 * @example
 *  fill("Hello World"); // Types "Hello World" in the active element
 * @example
 *  fill("Hello World", { instantly: true }); // Pastes "Hello World" in the active element
 * @example
 *  fill(new File(["Hello World"], "hello.txt")); // Uploads a file named "hello.txt" with "Hello World" as content
 */
export function fill(value, options) {
    const element = getActiveElement();

    if (!isEditable(element)) {
        throw new HootDomError(`cannot call \`fill()\`: target should be editable`);
    }

    _fill(element, value, options);

    return logEvents("fill");
}

/**
 * Performs a hover sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - `pointerover`
 *  - [desktop] `mouseover`
 *  - `pointerenter`
 *  - [desktop] `mouseenter`
 *  - `pointermove`
 *  - [desktop] `mousemove`
 *  - [touch] `touchmove`
 *
 * @param {Target} target
 * @param {PointerOptions} [options]
 * @returns {Event[]}
 * @example
 *  hover("button"); // Hovers the first <button> element
 */
export function hover(target, options) {
    const element = getFirstTarget(target, options);

    _hover(element, options);

    return logEvents("hover");
}

/**
 * Performs a key down sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
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
 * @param {KeyboardEventInit} [options]
 * @returns {Event[]}
 * @example
 *  keyDown(" "); // Space key
 */
export function keyDown(keyStrokes, options) {
    const eventInits = parseKeyStrokes(keyStrokes, options);
    for (const eventInit of eventInits) {
        _keyDown(getActiveElement(), eventInit);
    }

    return logEvents("keyDown");
}

/**
 * Performs a key up sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - `keyup`
 *
 * @param {KeyStrokes} keyStrokes
 * @param {KeyboardEventInit} [options]
 * @returns {Event[]}
 * @example
 *  keyUp("Enter");
 */
export function keyUp(keyStrokes, options) {
    const eventInits = parseKeyStrokes(keyStrokes, options);
    for (const eventInit of eventInits) {
        _keyUp(getActiveElement(), eventInit);
    }

    return logEvents("keyUp");
}

/**
 * Performs a leave sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - `pointermove`
 *  - [desktop] `mousemove`
 *  - [touch] `touchmove`
 *  - `pointerout`
 *  - [desktop] `mouseout`
 *  - `pointerleave`
 *  - [desktop] `mouseleave`
 *
 * @returns {Event[]}
 * @example
 *  leave("button"); // Moves out of <button>
 */
export function leave(options) {
    _hover(null, options);

    return logEvents("leave");
}

/**
 * Shorthand helper to attach an event listener to the given {@link Target}, and
 * returning a function to remove the listener.
 *
 * @template {EventType} T
 * @param {EventTarget | Target} target
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
 * Performs a pointer down on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - `pointerdown`
 *  - [desktop] `mousedown`
 *  - [touch] `touchstart`
 *  - [target is not active element] `blur`
 *  - [target is focusable] `focus`
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {Event[]}
 * @example
 *  pointerDown("button"); // Focuses to the first <button> element
 */
export function pointerDown(target, options) {
    const element = getFirstTarget(target, options);

    _implicitHover(element, options);
    _pointerDown(element, options);

    return logEvents("pointerDown");
}

/**
 * Performs a pointer up on the given {@link Target}.
 *
 * The event sequence is as follow:
 * - `pointerup`
 * - [desktop] `mouseup`
 * - [touch] `touchend`
 *
 * @param {Target} target
 * @param {QueryOptions} [options]
 * @returns {Event[]}
 * @example
 *  pointerUp("body"); // Triggers a pointer up on the <body> element
 */
export function pointerUp(target, options) {
    const element = getFirstTarget(target, options);

    _implicitHover(element, options);
    _pointerUp(element, options);

    return logEvents("pointerUp");
}

/**
 * Performs a keyboard event sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - `keydown`
 *  - `keyup`
 *
 * @param {KeyStrokes} keyStrokes
 * @param {KeyboardEventInit} [options]
 * @returns {Event[]}
 * @example
 *  pointerDown("button[type=submit]"); // Moves focus to <button>
 *  keyDown("Enter"); // Submits the form
 * @example
 *  keyDown("Shift+Tab"); // Focuses previous focusable element
 * @example
 *  keyDown(["ctrl", "v"]); // Pastes current clipboard content
 */
export function press(keyStrokes, options) {
    const eventInits = parseKeyStrokes(keyStrokes, options);
    const activeElement = getActiveElement();

    for (const eventInit of eventInits) {
        _keyDown(activeElement, eventInit);
    }
    for (const eventInit of eventInits.reverse()) {
        _keyUp(activeElement, eventInit);
    }

    return logEvents("press");
}

/**
 * Performs a resize event sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - `resize`
 *
 * The target will be resized to the given dimensions, enforced by `!important` style
 * attributes.
 *
 * @param {Dimensions} dimensions
 * @returns {Event[]}
 * @example
 *  resize("body", { width: 1000, height: 500 }); // Resizes <body> to 1000x500
 */
export function resize(dimensions) {
    const [width, height] = parseDimensions(dimensions);

    setDimensions(width, height);

    dispatch(getWindow(), "resize");

    return logEvents("resize");
}

/**
 * Performs a scroll event sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - [desktop] `wheel`
 *  - `scroll`
 *
 * @param {Target} target
 * @param {Position} position
 * @param {QueryOptions} [options]
 * @returns {Event[]}
 * @example
 *  scroll("body", { y: 0 }); // Scrolls to the top of <body>
 */
export function scroll(target, position, options) {
    /** @type {ScrollToOptions} */
    const scrollOptions = {};
    const [x, y] = parsePosition(position);
    if (!Number.isNaN(x)) {
        scrollOptions.left = x;
    }
    if (!Number.isNaN(y)) {
        scrollOptions.top = y;
    }
    const element = getFirstTarget(target, { ...options, scrollable: true });
    /** @type {Event[]} */
    if (!hasTouch()) {
        dispatch(element, "wheel");
    }
    // This will trigger a trusted "scroll" event
    element.scrollTo(scrollOptions);

    return logEvents("scroll");
}

/**
 * Performs a selection event sequence current active element. This helper is intended
 * for `<select>` elements only.
 *
 * The event sequence is as follow:
 *  - `change`
 *
 * @param {string | number | (string | number)[]} value
 * @param {SelectOptions} [options]
 * @returns {Event[]}
 * @example
 *  click("select[name=country]"); // Focuses <select> element
 *  select("belgium"); // Selects the <option value="belgium"> element
 */
export function select(value, options) {
    const element = options?.target ? getFirstTarget(options.target) : getActiveElement();
    if (!hasTagName(element, "select")) {
        throw new HootDomError(`cannot call \`select()\`: target should be a <select> element`);
    }

    if (options?.target) {
        _implicitHover(element);
        _pointerDown(element);
    }
    _select(element, value);
    if (options?.target) {
        _pointerUp(element);
    }

    return logEvents("select");
}

/**
 * Gives the given {@link File} list to the current file input. This helper only
 * works if a file input has been previously interacted with (by clicking on it).
 *
 * @param {MaybeIterable<File>} files
 */
export function setInputFiles(files) {
    if (!runTime.currentFileInput) {
        throw new HootDomError(
            `cannot call \`setInputFiles()\`: no file input has been interacted with`
        );
    }

    _fill(runTime.currentFileInput, files);

    runTime.currentFileInput = null;

    return logEvents("setInputFiles");
}

/**
 * @param {Target} target
 * @param {number} value
 * @param {PointerOptions} options
 */
export function setInputRange(target, value, options) {
    const element = getFirstTarget(target, options);

    _implicitHover(element, options);
    _pointerDown(element, options);
    _fill(element, value);
    _pointerUp(element, options);

    return logEvents("setInputRange");
}

/**
 * @param {HTMLElement} fixture
 */
export function setupEventActions(fixture) {
    if (runTime.currentPointerDownTimeout) {
        globalThis.clearTimeout(runTime.currentPointerDownTimeout);
    }

    removeChangeTargetListeners();

    fixture.addEventListener("click", registerFileInput, { capture: true });

    // Runtime global variables
    $assign(runTime, getDefaultRunTimeValue());

    // Special keys
    $assign(specialKeys, getDefaultSpecialKeysValue());
}

/**
 * Ensures that the given {@link Target} is unchecked.
 *
 * If it is checked, a click is triggered on the input.
 * If the input is still checked after the click, an error is thrown.
 *
 * @see {@link click}
 * @param {Target} target
 * @param {PointerOptions} [options]
 * @returns {Event[]}
 * @example
 *  uncheck("input[type=checkbox]"); // Unchecks the first <input> checkbox element
 */
export function uncheck(target, options) {
    const element = getFirstTarget(target, options);
    if (!isCheckable(element)) {
        throw new HootDomError(
            `cannot call \`uncheck()\`: target should be a checkbox or radio input`
        );
    }

    const checkTarget = getTag(element) === "label" ? element.control : element;
    if (checkTarget.checked) {
        _implicitHover(element, options);
        _click(element, options);

        if (checkTarget.checked) {
            throw new HootDomError(
                `error when calling \`uncheck()\`: target is still checked after interaction`
            );
        }
    }

    return logEvents("uncheck");
}

/**
 * Triggers a "beforeunload" event the current window.
 *
 * @returns {Event[]}
 */
export function unload() {
    dispatch(getWindow(), "beforeunload");
    return logEvents("unload");
}
