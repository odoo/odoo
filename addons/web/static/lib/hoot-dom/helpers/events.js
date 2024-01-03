/** @odoo-module */

import { HootDomError, getTag, isFirefox, isIterable } from "../hoot_dom_utils";
import {
    getActiveElement,
    getDefaultRootNode,
    getNextFocusableElement,
    getPreviousFocusableElement,
    getRect,
    getWindow,
    isCheckable,
    isEditable,
    isEventTarget,
    isNodeFocusable,
    parsePosition,
    queryAll,
    queryOne,
    setDimensions,
    toSelector,
} from "./dom";

/**
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
 *  confirm?: boolean;
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
    console,
    DataTransfer,
    document,
    matchMedia,
    navigator,
    Object,
    ontouchstart,
    String,
    Touch,
    TypeError,
} = globalThis;

//-----------------------------------------------------------------------------
// Internal
//-----------------------------------------------------------------------------

/**
 * @template T
 * @param {MaybeIterable<T>} value
 * @returns {T[]}
 */
const ensureArray = (value) => (isIterable(value) ? [...value] : [value]);

/**
 * Returns the list of nodes containing n2 (included) that do not contain n1.
 *
 * @param {Element} el1
 * @param {Element} el2
 */
const getDifferentParents = (el1, el2) => {
    const parents = [el2];
    while (parents[0].parentElement) {
        const parent = parents[0].parentElement;
        if (parent.contains(el1)) {
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
        case "keypress":
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
        return toEventPosition(posX, posY);
    }

    const { x, y, width, height } = getRect(element);
    let clientX = Math.floor(x);
    let clientY = Math.floor(y);

    if (isString) {
        const positions = position.split("-");

        // X position
        if (positions.includes("left")) {
            clientX -= 1;
        } else if (positions.includes("right")) {
            clientX += Math.ceil(width) + 1;
        } else {
            clientX += Math.floor(width / 2);
        }

        // Y position
        if (positions.includes("top")) {
            clientY -= 1;
        } else if (positions.includes("bottom")) {
            clientY += Math.ceil(height) + 1;
        } else {
            clientY += Math.floor(height / 2);
        }
    } else {
        // X position
        if (Number.isNaN(posX)) {
            clientX += Math.floor(width / 2);
        } else {
            if (relative) {
                clientX += posX || 0;
            } else {
                clientX = posX || 0;
            }
        }

        // Y position
        if (Number.isNaN(posY)) {
            clientY += Math.floor(height / 2);
        } else {
            if (relative) {
                clientY += posY || 0;
            } else {
                clientY = posY || 0;
            }
        }
    }

    return toEventPosition(clientX, clientY);
};

/**
 * @param {Node} node
 * @param  {...string} tagNames
 */
const hasTagName = (node, ...tagNames) => tagNames.includes(getTag(node));

const hasTouch = () => ontouchstart !== undefined || matchMedia("(pointer:coarse)").matches;

const isMacOS = () => /Mac/i.test(navigator.userAgent);

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
    console.groupCollapsed(...groupName);
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
        if (event.target) {
            const targetParts = toSelector(event.target, { object: true });
            colors.push("blue");
            if (targetParts.id) {
                colors.push("orange");
            }
            if (targetParts.class) {
                colors.push("lightBlue");
            }
            const targetString = Object.values(targetParts)
                .map((part) => `%c${part}%c`)
                .join("");
            message += ` @${targetString}`;
        }
        const messageColors = colors.flatMap((color) => [
            `color: ${LOG_COLORS[color]}; font-weight: normal`,
            `color: ${LOG_COLORS.reset}`,
        ]);

        console.groupCollapsed(message, ...messageColors);
        console.dir(event);
        console.log(event.target);
        console.groupEnd(message);
    }
    console.groupEnd(...groupName);
    return events;
};

/**
 * @param {KeyStrokes} keyStrokes
 */
const parseKeyStroke = (keyStrokes) =>
    (isIterable(keyStrokes) ? [...keyStrokes] : [keyStrokes])
        .flatMap((keyStroke) => keyStroke.split(/[,+]+/))
        .map((key) => ({ key }));

/**
 * @param {EventTarget} target
 * @param {string} initialValue
 */
const registerForChange = (target, initialValue) => {
    const triggerChange = () => {
        for (const removeListener of removeChangeTargetListeners) {
            removeListener();
        }
        if (target.value !== initialValue) {
            dispatch(target, "change");
        }
    };

    removeChangeTargetListeners = [
        on(target, "keydown", (ev) => ev.key === "Enter" && triggerChange()),
        on(target, "blur", triggerChange),
    ];
};

/**
 * @param {KeyboardEventInit} eventInit
 * @param {boolean} toggle
 */
const registerSpecialKey = (eventInit, toggle) => {
    switch (eventInit.key.toLowerCase()) {
        case "alt":
            if (isMacOS()) {
                specialKeys.ctrlKey = toggle;
            } else {
                specialKeys.altKey = toggle;
            }
            break;
        case "ctrl":
        case "control":
            if (isMacOS()) {
                specialKeys.metaKey = toggle;
            } else {
                specialKeys.ctrlKey = toggle;
            }
            break;
        case "caps":
        case "shift":
            specialKeys.shiftKey = toggle;
            break;
    }
};

/**
 * @param {number} x
 * @param {number} y
 */
const toEventPosition = (x, y) => {
    x ||= 0;
    y ||= 0;
    return {
        clientX: x,
        clientY: y,
        pageX: x,
        pageY: y,
        screenX: x,
        screenY: y,
    };
};

/**
 * @param {EventTarget} target
 * @param {PointerEventInit} eventInit
 */
const triggerClick = (target, pointerInit) => {
    const events = [dispatch(target, "click", pointerInit)];
    if (isPrevented(events[0])) {
        return events;
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
                    events.push(dispatch(target, "change"));
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
                    return [...events, ...triggerClick(target, pointerInit)];
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
                    events.push(dispatch(parent, "change"));
                }
                break;
            }
        }
    }
    return events;
};

/**
 * @param {EventTarget} target
 */
const triggerFocus = (target) => {
    /** @type {Event[]} */
    const events = [];
    const previous = getActiveElement(target);
    if (previous === target) {
        return events;
    }
    if (previous !== target.ownerDocument.body) {
        events.push(dispatch(previous, "blur", { relatedTarget: target }));
    }
    if (isNodeFocusable(target)) {
        events.push(dispatch(target, "focus", { relatedTarget: previous }));
        if (!isNil(target.selectionStart) && !isNil(target.selectionEnd)) {
            target.selectionStart = target.selectionEnd = target.value.length;
        }
    }
    return events;
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
    // - Ctrl + A: selects all the text
    // - Backspace: deletes the text
    fullClear = true;
    const events = [
        _press(target, { ctrlKey: true, key: "a" }),
        _press(target, { key: "Backspace" }),
    ];
    fullClear = false;

    registerForChange(target, initialValue);

    if (options?.confirm) {
        events.push(_press(target, { key: "Enter" }));
    }
};

/**
 * @param {EventTarget} target
 * @param {PointerOptions} [options]
 */
const _click = (target, options) => {
    const pointerInit = {
        ...getPosition(target, options),
        button: options?.button || 0,
    };
    const events = [..._pointerDown(target, pointerInit), ..._pointerUp(target, pointerInit)];
    return events;
};

/**
 * @param {EventTarget} target
 * @param {InputValue} value
 * @param {FillOptions} [options]
 */
const _fill = (target, value, options) => {
    /** @type {Event[]} */
    const events = [];
    const initialValue = target.value;

    if (getTag(target) === "input" && target.type === "file") {
        const dataTransfer = new DataTransfer();
        if (target.multiple) {
            // Keep previous files
            for (const file of target.files) {
                dataTransfer.items.add(file);
            }
        }
        for (const file of ensureArray(value)) {
            if (!(file instanceof File)) {
                throw new TypeError(`file input only accept 'File' objects`);
            }
            dataTransfer.items.add(file);
        }
        target.files = dataTransfer.files;
    } else {
        if (options?.instantly) {
            // Simulates filling the clipboard with the value (can be from external source)
            navigator.clipboard.writeTextSync(value);
            events.push(..._press(target, { ctrlKey: true, key: "v" }));
        } else {
            if (options?.composition) {
                isComposing = true;
                // Simulates the start of a composition
                events.push(dispatch(target, "compositionstart"));
            }
            for (const char of String(value)) {
                const key = char.toLowerCase();
                events.push(..._press(target, { key, shiftKey: key !== char }));
            }
            if (options?.composition) {
                isComposing = false;
                // Simulates the end of a composition
                events.push(dispatch(target, "compositionend"));
            }
        }
    }

    registerForChange(target, initialValue);

    if (options?.confirm) {
        events.push(_press(target, { key: "Enter" }));
    }

    return events;
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _keyDown = (target, eventInit) => {
    const events = [dispatch(target, "keydown", eventInit)];
    registerSpecialKey(eventInit, true);

    let inputData = null;
    let inputType = null;
    let nextValue = target.value;
    let prevented = isPrevented(events[0]);

    if (!prevented) {
        if (isEditable(target)) {
            switch (eventInit.key) {
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
                default: {
                    if (eventInit.key.length === 1 && !eventInit.ctrlKey) {
                        // Character coming from the keystroke
                        // ! TODO: Doesn't work with non-roman locales
                        const { selectionStart, selectionEnd, value } = target;
                        inputData = eventInit.shiftKey
                            ? eventInit.key.toUpperCase()
                            : eventInit.key.toLowerCase();
                        // Insert character in target value
                        if (isNil(selectionStart) && isNil(selectionEnd)) {
                            nextValue += inputData;
                        } else {
                            nextValue =
                                value.slice(0, selectionStart) +
                                inputData +
                                value.slice(selectionEnd);
                        }
                        inputType = isComposing ? "insertCompositionText" : "insertText";
                    }
                }
            }
        }

        // Trigger 'keypress' event for printable characters
        if (!eventInit.ctrlKey && /^[\w ]$/.test(eventInit.key)) {
            const keyPressEvent = dispatch(target, "keypress", eventInit);
            events.push(keyPressEvent);
            prevented = isPrevented(keyPressEvent);
        }
    }

    if (!prevented) {
        switch (eventInit.key) {
            case "a": {
                if (eventInit.ctrlKey) {
                    // Select all
                    if (isEditable(target)) {
                        events.push(dispatch(target, "select"));
                    } else {
                        const selection = globalThis.getSelection();
                        const range = document.createRange();
                        range.selectNodeContents(target);
                        selection.removeAllRanges();
                        selection.addRange(range);
                    }
                }
                break;
            }
            /**
             * Special action: shift focus
             *  On: unprevented 'Tab' keydown
             *  Do: focus next (or previous with 'shift') focusable element
             */
            case "Tab": {
                const next = eventInit.shiftKey
                    ? getPreviousFocusableElement()
                    : getNextFocusableElement();
                if (next) {
                    events.push(...triggerFocus(next));
                }
                break;
            }
            /**
             * Special action: copy
             *  On: unprevented 'ctrl + c' keydown
             *  Do: copy current selection to clipboard
             */
            case "c": {
                if (eventInit.ctrlKey) {
                    // Get selection from window
                    const text = globalThis.getSelection().toString();
                    globalThis.navigator.clipboard.writeTextSync(text);
                }
                break;
            }
            /**
             * Special action: paste
             *  On: unprevented 'ctrl + v' keydown on editable element
             *  Do: paste current clipboard content to current element
             */
            case "v": {
                if (eventInit.ctrlKey && isEditable(target)) {
                    // Set target value (synchonously)
                    const value = globalThis.navigator.clipboard.readTextSync();
                    nextValue = value;

                    inputType = "insertFromPaste";
                }
                break;
            }
            /**
             * Special action: cut
             *  On: unprevented 'ctrl + x' keydown on editable element
             *  Do: cut current selection to clipboard and remove selection
             */
            case "x": {
                if (eventInit.ctrlKey && isEditable(target)) {
                    // Get selection from window
                    const text = globalThis.getSelection().toString();
                    globalThis.navigator.clipboard.writeTextSync(text);

                    nextValue = deleteSelection(target);
                    inputType = "deleteByCut";
                }
                break;
            }
        }

        if (target.value !== nextValue) {
            target.value = nextValue;
            events.push(
                dispatch(target, "input", {
                    data: inputData,
                    inputType,
                })
            );
        }
    }

    return events;
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _keyUp = (target, eventInit) => {
    registerSpecialKey(eventInit, false);
    return [dispatch(target, "keyup", eventInit)];
};

/**
 * @param {EventTarget} target
 * @param {PointerEventInit} eventInit
 */
const _pointerDown = (target, eventInit) => {
    currentPointerTarget = target;
    if (currentPointerTarget !== previousPointerTarget) {
        currentClickCount = 0;
    }

    const events = [dispatch(target, "pointerdown", eventInit)];
    if (!isPrevented(events[0])) {
        // pointer events are triggered along their related counterparts:
        // - mouse events in desktop environment
        // - touch events in mobile environment
        const relatedType = hasTouch() ? "touchstart" : "mousedown";
        const relatedEvent = dispatch(target, relatedType, eventInit);
        events.push(relatedEvent);

        if (!isPrevented(relatedEvent)) {
            // Focus the element (if focusable)
            events.push(...triggerFocus(target));
            if (eventInit.button === 2) {
                /**
                 * Special action: context menu
                 *  On: unprevented 'pointerdown' with right click and its related
                 *      event on an element
                 *  Do: triggers a 'contextmenu' event
                 */
                events.push(dispatch(target, "contextmenu", eventInit));
            }
        }
    }

    return events;
};

/**
 * @param {EventTarget} target
 * @param {PointerEventInit} eventInit
 */
const _pointerUp = (target, eventInit) => {
    const events = [dispatch(target, "pointerup", eventInit)];
    if (!events.some(isPrevented)) {
        // pointer events are triggered along their related counterparts:
        // - mouse events in desktop environment
        // - touch events in mobile environment
        const relatedType = hasTouch() ? "touchend" : "mouseup";
        events.push(dispatch(target, relatedType, eventInit));
    }

    if (target === currentPointerTarget && !events.some(isPrevented)) {
        previousPointerTarget = currentPointerTarget;

        events.push(...triggerClick(target, eventInit));
        currentClickCount++;
        if (!hasTouch() && currentClickCount % 2 === 0) {
            events.push(dispatch(target, "dblclick", eventInit));
        }
    }

    currentPointerTarget = null;
    currentPointerTimeout = globalThis.setTimeout(() => {
        // Use `globalThis.setTimeout` to potentially make use of the mock timeouts
        // since the events run in the same temporal context as the tests
        currentClickCount = 0;
        currentPointerTimeout = 0;
    }, DOUBLE_CLICK_DELAY);

    return events;
};

/**
 * @param {EventTarget} target
 * @param {KeyboardEventInit} eventInit
 */
const _press = (target, eventInit) => {
    const keyDownEvents = _keyDown(target, eventInit);
    const events = [...keyDownEvents, ..._keyUp(target, eventInit)];

    if (!isPrevented(keyDownEvents[0])) {
        if (eventInit.key === "Enter") {
            let parentForm;
            if (getTag(target) === "button" && target.type === "button") {
                /**
                 * Special action: button 'Enter'
                 *  On: unprevented 'Enter' keydown & keypress on a <button type="button"/>
                 *  Do: triggers a 'click' event on the button
                 */
                events.push(...triggerClick(target, { button: 0 }));
            } else if ((parentForm = target.closest("form"))) {
                /**
                 * Special action: form 'Enter'
                 *  On: unprevented 'Enter' keydown & keypress on any element that
                 *      is not a <button type="button"/> in a form element
                 *  Do: triggers a 'submit' event on the form
                 */
                events.push(dispatch(parentForm, "submit"));
            }
        }
        if (eventInit.key === " " && getTag(target) === "input" && target.type === "checkbox") {
            /**
             * Special action: input[type=checkbox] 'Space'
             *  On: unprevented ' ' keydown & keypress on an <input type="checkbox"/>
             *  Do: triggers a 'click' event on the input
             */
            events.push(...triggerClick(target, { button: 0 }));
        }
    }

    return events;
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
    const events = dispatch(target, "change");
    return events;
};

const DOUBLE_CLICK_DELAY = 500;
const LOG_COLORS = {
    blue: "#5db0d7",
    orange: "#f29364",
    lightBlue: "#9bbbdc",
    reset: "inherit",
};
const SPECIAL_EVENTS = ["blur", "focus", "select", "submit"];
let allowLogs = false;
/** @type {Event[]} */
let currentEvents = [];
let fullClear = false;

// Keyboard global variables
const specialKeys = {
    altKey: false,
    ctrlKey: false,
    metaKey: false,
    shiftKey: false,
};
let isComposing = false;
let removeChangeTargetListeners = [];

// Pointer global variables
let currentClickCount = 0;
let currentPointerTarget = null;
let currentPointerTimeout = 0;
let previousPointerTarget = null;

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
 * - cannot be canceled
 * @param {EventInit} [eventInit]
 */
const mapNonBubblingEvent = (eventInit) => ({
    composed: true,
    ...eventInit,
    bubbles: false,
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
const mapInputEvent = (eventInit) => ({
    composed: isComposing,
    data: null,
    isComposing,
    view: getWindow(),
    ...mapBubblingEvent(eventInit),
});

/**
 * @param {TouchEventInit} [eventInit]
 */
const mapKeyboardEvent = (eventInit) => ({
    ...specialKeys,
    composed: isComposing,
    isComposing,
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

    _click(element, options);
    _click(element, options);

    return logEvents("dblclick");
}

/**
 * Creates a new {@link Event} of the given type and dispatches it on the given
 * {@link Target}.
 *
 * Note that this function is free of side-effects and does not trigger any other
 * event or special action (except the functions related to the event type, such
 * as `blur()` for the `"blur"` event).
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
    const [Constructor, processParams] = getEventConstructor(type);
    const event = new Constructor(type, processParams({ ...eventInit, target }));

    target.dispatchEvent(event);
    currentEvents.push(event);

    // Check special methods
    if (!event.defaultPrevented && SPECIAL_EVENTS.includes(type)) {
        target[type]();
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
                fn(...args);
                if (endDrag) {
                    dragEndReason = fn.name;
                }
            },
        }[fn.name];
    };

    const cancel = expectIsDragging(
        /** @type {DragHelpers["cancel"]} */
        function cancel() {
            _press(getWindow(), { key: "Escape" });
            return logEvents("cancel");
        },
        true
    );

    const drop = expectIsDragging(
        /** @type {DragHelpers["drop"]} */
        function drop(to, options) {
            if (to) {
                moveTo(to, options);
            }
            _pointerUp(currentTarget || source, targetPosition);
            if (canTriggerDragEvents) {
                /**
                 * Special action: drag events
                 *  On: unprevented 'pointerdown' and related events not immediatly
                 *      followed by a pointer up sequence
                 *  Do: trigger drag events along the pointer events
                 */
                dispatch(currentTarget || source, "dragend", targetPosition);
            }
            return logEvents("drop");
        },
        true
    );

    const moveTo = expectIsDragging(
        /** @type {DragHelpers["moveTo"]} */
        function moveTo(to, options) {
            currentTarget = queryOne(to);
            if (!currentTarget) {
                return;
            }

            // Recompute target position
            targetPosition = getPosition(currentTarget, options);

            // Move, enter and drop the element on the target
            dispatch(source, "pointermove", targetPosition);
            if (!hasTouch()) {
                dispatch(source, "mousemove", targetPosition);
            }
            if (canTriggerDragEvents) {
                dispatch(source, "drag", targetPosition);
            }

            // "pointerenter" is fired on every parent of `target` that do not contain
            // `from` (typically: different parent lists).
            for (const parent of getDifferentParents(source, currentTarget)) {
                dispatch(parent, "pointerenter", targetPosition);
                if (!hasTouch()) {
                    dispatch(source, "mouseenter", targetPosition);
                }
                if (canTriggerDragEvents) {
                    dispatch(parent, "dragenter", targetPosition);
                }
            }

            return dragHelpers;
        },
        false
    );

    const dragHelpers = { cancel, drop, moveTo };

    const source = queryOne(target);

    let dragEndReason = null;
    let currentTarget;
    let targetPosition;

    // Pointer down on main target
    const startEventInit = {
        ...getPosition(source, options),
        button: options?.button || 0,
    };

    const pointerDownEvents = _pointerDown(source, startEventInit);
    const canTriggerDragEvents =
        source.draggable && !pointerDownEvents.slice(0, 2).some(isPrevented);

    if (canTriggerDragEvents) {
        dispatch(source, "dragstart", startEventInit);
    }

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

    _clear(element);
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
 *
 * @param {Target} target
 * @param {PointerOptions} [options]
 * @returns {Event[]}
 * @example
 *  hover("button"); // Hovers the first <button> element
 */
export function hover(target, options) {
    const element = getFirstTarget(target, options);
    const position = getPosition(element, options);
    dispatch(element, "pointerover", position);
    if (!hasTouch()) {
        dispatch(element, "mouseover", position);
    }
    dispatch(element, "pointerenter", position);
    if (!hasTouch()) {
        dispatch(element, "mouseenter", position);
    }
    dispatch(element, "pointermove", position);
    if (!hasTouch()) {
        dispatch(element, "mousemove", position);
    }

    return logEvents("hover");
}

/**
 * Performs a key down sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - `keydown`
 *  - `keypress`
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
 * @returns {Event[]}
 * @example
 *  keyDown(" "); // Space key
 */
export function keyDown(keyStrokes) {
    const eventInits = parseKeyStroke(keyStrokes);
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
 * @returns {Event[]}
 * @example
 *  keyUp("Enter");
 */
export function keyUp(keyStrokes) {
    const eventInits = parseKeyStroke(keyStrokes).reverse();
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
 *  - `pointerout`
 *  - [desktop] `mouseout`
 *  - `pointerleave`
 *  - [desktop] `mouseleave`
 *
 * @param {Target} target
 * @param {PointerOptions} [options]
 * @returns {Event[]}
 * @example
 *  leave("button"); // Moves out of <button>
 */
export function leave(target, options) {
    for (const element of queryAll(target, options)) {
        const position = getPosition(options);
        dispatch(element, "pointermove", position);
        if (!hasTouch()) {
            dispatch(element, "mousemove", position);
        }
        dispatch(element, "pointerout", position);
        if (!hasTouch()) {
            dispatch(element, "mouseout", position);
        }
        dispatch(element, "pointerleave", position);
        if (!hasTouch()) {
            dispatch(element, "mouseleave", position);
        }
    }

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
    const pointerInit = {
        ...getPosition(element, options),
        button: options?.button || 0,
    };
    _pointerDown(element, pointerInit);

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
    const pointerInit = {
        ...getPosition(element, options),
        button: options?.button || 0,
    };
    _pointerUp(element, pointerInit);

    return logEvents("pointerUp");
}

/**
 * Performs a keyboard event sequence on the given {@link Target}.
 *
 * The event sequence is as follow:
 *  - `keydown`
 *  - `keypress`
 *  - `keyup`
 *
 * @param {KeyStrokes} keyStrokes
 * @returns {Event[]}
 * @example
 *  pointerDown("button[type=submit]"); // Moves focus to <button>
 *  keyDown("Enter"); // Submits the form
 * @example
 *  keyDown("Shift+Tab"); // Focuses previous focusable element
 * @example
 *  keyDown(["Ctrl", "v"]); // Pastes current clipboard content
 */
export function press(keyStrokes) {
    const eventInits = parseKeyStroke(keyStrokes);
    for (const eventInit of eventInits) {
        _press(getActiveElement(), eventInit);
    }

    return logEvents("press");
}

export function resetEventActions() {
    if (currentPointerTimeout) {
        globalThis.clearTimeout(currentPointerTimeout);
    }
    for (const removeListener of removeChangeTargetListeners) {
        removeListener();
    }

    isComposing = false;
    removeChangeTargetListeners = [];

    currentClickCount = 0;
    currentPointerTarget = null;
    currentPointerTimeout = 0;

    // Special keys
    specialKeys.altKey = false;
    specialKeys.ctrlKey = false;
    specialKeys.metaKey = false;
    specialKeys.shiftKey = false;
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
 * @param {Target} target
 * @param {Dimensions} dimensions
 * @param {QueryOptions} [options]
 * @returns {Event[]}
 * @example
 *  resize("body", { width: 1000, height: 500 }); // Resizes <body> to 1000x500
 */
export function resize(target, dimensions, options) {
    const [width, height] = parseDimensions(dimensions);
    const element = getFirstTarget(target, options);
    if (element === getDefaultRootNode()) {
        setDimensions(width, height);
    } else {
        if (width !== null) {
            element.style.setProperty("width", `${width}px`, "important");
        }
        if (height !== null) {
            element.style.setProperty("height", `${height}px`, "important");
        }
    }
    dispatch(element, "resize");

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
    if (x !== null) {
        scrollOptions.left = x;
    }
    if (y !== null) {
        scrollOptions.top = y;
    }
    const element = getFirstTarget(target, { ...options, scrollable: true });
    /** @type {Event[]} */
    if (!hasTouch()) {
        dispatch(target, "wheel");
    }
    element.scrollTo(scrollOptions);
    dispatch(element, "scroll");

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
 * @returns {Event[]}
 * @example
 *  click("select[name=country]"); // Focuses <select> element
 *  select("belgium"); // Selects the <option value="belgium"> element
 */
export function select(value) {
    const element = getActiveElement();
    if (!hasTagName(element, "select")) {
        throw new HootDomError(`cannot call \`select()\`: target should be a <select> element`);
    }

    _select(element, value);

    return logEvents("select");
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
        _click(element, options);

        if (checkTarget.checked) {
            throw new HootDomError(
                `error when calling \`uncheck()\`: target is still checked after interaction`
            );
        }
    }

    return logEvents("uncheck");
}
