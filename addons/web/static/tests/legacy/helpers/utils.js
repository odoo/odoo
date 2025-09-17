/** @odoo-module alias=@web/../tests/helpers/utils default=false */

import { Deferred } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { isVisible } from "@web/core/utils/ui";
import { registerCleanup } from "./cleanup";

/**
 * Applies a fixed time zone to luxon based on an offset to the UTC time zone.
 *
 * @param {number} offset the number of minutes ahead or behind the UTC time zone
 *                          +120 => UTC+2
 *                          -120 => UTC-2
 */
export function patchTimeZone(offset) {
    patchWithCleanup(luxon.Settings, { defaultZone: luxon.FixedOffsetZone.instance(offset) });
}

/**
 *
 * @param {Object} obj object to patch
 * @param {Object} patchValue the actual patch description
 */
export function patchWithCleanup(obj, patchValue) {
    const unpatch = patch(obj, patchValue);
    registerCleanup(() => {
        unpatch();
    });
}

/**
 * @returns {Element}
 */
export function getFixture() {
    if (!window.QUnit) {
        return document;
    }
    if (QUnit.config.debug) {
        return document.body;
    } else {
        return document.getElementById("qunit-fixture");
    }
}

export async function nextTick() {
    await new Promise((resolve) => window.requestAnimationFrame(resolve));
    await new Promise((resolve) => setTimeout(resolve));
}

export function makeDeferred() {
    return new Deferred();
}

function findElement(el, selector) {
    let target = el;
    if (selector) {
        const els = el.querySelectorAll(selector);
        if (els.length === 0) {
            throw new Error(`No element found (selector: ${selector})`);
        }
        if (els.length > 1) {
            throw new Error(`Found ${els.length} elements, instead of 1 (selector: ${selector})`);
        }
        target = els[0];
    }
    return target;
}

//-----------------------------------------------------------------------------
// Event init attributes mappers
//-----------------------------------------------------------------------------

/** @param {EventInit} [args] */
const mapBubblingEvent = (args) => ({ ...args, bubbles: true });

/** @param {EventInit} [args] */
const mapNonBubblingEvent = (args) => ({ ...args, bubbles: false });

/** @param {EventInit} [args={}] */
const mapBubblingPointerEvent = (args = {}) => ({
    clientX: args.pageX,
    clientY: args.pageY,
    ...args,
    bubbles: true,
    cancelable: true,
    view: window,
});

/** @param {EventInit} [args] */
const mapNonBubblingPointerEvent = (args) => ({
    ...mapBubblingPointerEvent(args),
    bubbles: false,
    cancelable: false,
});

/** @param {EventInit} [args={}] */
const mapCancelableTouchEvent = (args = {}) => ({
    ...args,
    bubbles: true,
    cancelable: true,
    composed: true,
    rotation: 0.0,
    touches: args.touches ? [...args.touches.map((e) => new Touch(e))] : undefined,
    view: window,
    zoom: 1.0,
});

/** @param {EventInit} [args] */
const mapNonCancelableTouchEvent = (args) => ({
    ...mapCancelableTouchEvent(args),
    cancelable: false,
});

/** @param {EventInit} [args] */
const mapKeyboardEvent = (args) => ({
    ...args,
    bubbles: true,
    cancelable: true,
});

/**
 * @template {typeof Event} T
 * @param {EventType} eventType
 * @returns {[T, (attrs: EventInit) => EventInit]}
 */
const getEventConstructor = (eventType) => {
    switch (eventType) {
        // Mouse events
        case "auxclick":
        case "click":
        case "contextmenu":
        case "dblclick":
        case "mousedown":
        case "mouseup":
        case "mousemove":
        case "mouseover":
        case "mouseout": {
            return [MouseEvent, mapBubblingPointerEvent];
        }
        case "mouseenter":
        case "mouseleave": {
            return [MouseEvent, mapNonBubblingPointerEvent];
        }
        // Pointer events
        case "pointerdown":
        case "pointerup":
        case "pointermove":
        case "pointerover":
        case "pointerout": {
            return [PointerEvent, mapBubblingPointerEvent];
        }
        case "pointerenter":
        case "pointerleave": {
            return [PointerEvent, mapNonBubblingPointerEvent];
        }
        // Focus events
        case "focusin": {
            return [FocusEvent, mapBubblingEvent];
        }
        case "focus":
        case "blur": {
            return [FocusEvent, mapNonBubblingEvent];
        }
        // Clipboard events
        case "cut":
        case "copy":
        case "paste": {
            return [ClipboardEvent, mapBubblingEvent];
        }
        // Keyboard events
        case "keydown":
        case "keypress":
        case "keyup": {
            return [KeyboardEvent, mapKeyboardEvent];
        }
        // Drag events
        case "drag":
        case "dragend":
        case "dragenter":
        case "dragstart":
        case "dragleave":
        case "dragover":
        case "drop": {
            return [DragEvent, mapBubblingEvent];
        }
        // Input events
        case "input": {
            return [InputEvent, mapBubblingEvent];
        }
        // Composition events
        case "compositionstart":
        case "compositionend": {
            return [CompositionEvent, mapBubblingEvent];
        }
        // UI events
        case "scroll": {
            return [UIEvent, mapNonBubblingEvent];
        }
        // Touch events
        case "touchstart":
        case "touchend":
        case "touchmove": {
            return [TouchEvent, mapCancelableTouchEvent];
        }
        case "touchcancel": {
            return [TouchEvent, mapNonCancelableTouchEvent];
        }
        // Default: base Event constructor
        default: {
            return [Event, mapBubblingEvent];
        }
    }
};

/**
 * @template {EventType} T
 * @param {Element} el
 * @param {string | null | undefined | false} selector
 * @param {T} eventType
 * @param {EventInit} [eventInit]
 * @param {TriggerEventOptions} [options={}]
 * @returns {GlobalEventHandlersEventMap[T] | Promise<GlobalEventHandlersEventMap[T]>}
 */
export function triggerEvent(el, selector, eventType, eventInit, options = {}) {
    const errors = [];
    const target = findElement(el, selector);

    // Error handling
    if (typeof eventType !== "string") {
        errors.push("event type must be a string");
    }
    if (!target) {
        errors.push("cannot find target");
    } else if (!options.skipVisibilityCheck && !isVisible(target)) {
        errors.push("target is not visible");
    }
    if (errors.length) {
        throw new Error(
            `Cannot trigger event${eventType ? ` "${eventType}"` : ""}${
                selector ? ` (with selector "${selector}")` : ""
            }: ${errors.join(" and ")}`
        );
    }

    // Actual dispatch
    const [Constructor, processParams] = getEventConstructor(eventType);
    const event = new Constructor(eventType, processParams(eventInit));
    target.dispatchEvent(event);

    if (window.QUnit && QUnit.config.debug) {
        const group = `%c[${event.type.toUpperCase()}]`;
        console.groupCollapsed(group, "color: #b52c9b");
        console.log(target, event);
        console.groupEnd(group, "color: #b52c9b");
    }

    if (options.sync) {
        return event;
    } else {
        return nextTick().then(() => event);
    }
}

/**
 * @param {Element} el
 * @param {string | null | undefined | false} selector
 * @param {(EventType | [EventType, EventInit])[]} [eventDefs]
 * @param {TriggerEventOptions} [options={}]
 */
export function triggerEvents(el, selector, eventDefs, options = {}) {
    const events = [...eventDefs].map((eventDef) => {
        const [eventType, eventInit] = Array.isArray(eventDef) ? eventDef : [eventDef, {}];
        return triggerEvent(el, selector, eventType, eventInit, options);
    });
    if (options.sync) {
        return events;
    } else {
        return nextTick().then(() => events);
    }
}

export function click(
    el,
    selector,
    { mouseEventInit = {}, skipDisabledCheck = false, skipVisibilityCheck = false } = {}
) {
    if (!skipDisabledCheck && el.disabled) {
        throw new Error("Can't click on a disabled button");
    }
    return triggerEvents(
        el,
        selector,
        [
            "pointerdown",
            "mousedown",
            "focus",
            "focusin",
            "pointerup",
            "mouseup",
            ["click", mouseEventInit],
        ],
        { skipVisibilityCheck }
    );
}
