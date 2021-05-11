/** @odoo-module **/

import { isMacOS } from "@web/core/browser/feature_detection";
import { patch, unpatch } from "@web/core/utils/patch";
import { registerCleanup } from "./cleanup";
import { download } from "@web/core/network/download";

const { Settings } = luxon;

/**
 * Patch the native Date object
 *
 * Note that it will be automatically unpatched at the end of the test
 *
 * @param {number} [year]
 * @param {number} [month]
 * @param {number} [day]
 * @param {number} [hours]
 * @param {number} [minutes]
 * @param {number} [seconds]
 */
export function patchDate(year, month, day, hours, minutes, seconds) {
    const actualDate = new Date();
    const fakeDate = new Date(year, month, day, hours, minutes, seconds);
    const timeInterval = actualDate.getTime() - fakeDate.getTime();
    const originalNow = Settings.now;
    Settings.now = () => Date.now() - timeInterval;
    registerCleanup(() => {
        Settings.now = originalNow;
    });
}

let nextId = 1;

/**
 *
 * @param {Object} obj object to patch
 * @param {Object} patchValue the actual patch description
 * @param {{pure?: boolean}} [options]
 */
export function patchWithCleanup(obj, patchValue, options) {
    const patchName = `__test_patch_${nextId++}__`;
    patch(obj, patchName, patchValue, options);
    registerCleanup(() => {
        unpatch(obj, patchName);
    });
}

export function getFixture() {
    if (QUnit.config.debug) {
        return document.body;
    } else {
        return document.querySelector("#qunit-fixture");
    }
}

export async function nextTick() {
    await new Promise((resolve) => window.requestAnimationFrame(resolve));
    await new Promise((resolve) => setTimeout(resolve));
}

export function makeDeferred() {
    let resolve;
    let reject;
    let prom = new Promise((res, rej) => {
        resolve = res;
        reject = rej;
    });
    prom.resolve = resolve;
    prom.reject = reject;
    return prom;
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

const keyboardEventBubble = (args) =>
    Object.assign({}, args, { bubbles: true, keyCode: args.which });

const mouseEventMapping = (args) =>
    Object.assign({}, args, {
        bubbles: true,
        cancelable: true,
        clientX: args ? args.pageX : undefined,
        clientY: args ? args.pageY : undefined,
        view: window,
    });

const mouseEventNoBubble = (args) =>
    Object.assign({}, args, {
        bubbles: false,
        cancelable: false,
        clientX: args ? args.pageX : undefined,
        clientY: args ? args.pageY : undefined,
        view: window,
    });

const noBubble = (args) => Object.assign({}, args, { bubbles: false });

const onlyBubble = (args) => Object.assign({}, args, { bubbles: true });

// TriggerEvent constructor/args processor mapping
const EVENT_TYPES = {
    auxclick: { constructor: MouseEvent, processParameters: mouseEventMapping },
    click: { constructor: MouseEvent, processParameters: mouseEventMapping },
    contextmenu: { constructor: MouseEvent, processParameters: mouseEventMapping },
    dblclick: { constructor: MouseEvent, processParameters: mouseEventMapping },
    mousedown: { constructor: MouseEvent, processParameters: mouseEventMapping },
    mouseup: { constructor: MouseEvent, processParameters: mouseEventMapping },
    mousemove: { constructor: MouseEvent, processParameters: mouseEventMapping },
    mouseenter: { constructor: MouseEvent, processParameters: mouseEventNoBubble },
    mouseleave: { constructor: MouseEvent, processParameters: mouseEventNoBubble },
    mouseover: { constructor: MouseEvent, processParameters: mouseEventMapping },
    mouseout: { constructor: MouseEvent, processParameters: mouseEventMapping },
    focus: { constructor: FocusEvent, processParameters: noBubble },
    focusin: { constructor: FocusEvent, processParameters: onlyBubble },
    blur: { constructor: FocusEvent, processParameters: noBubble },
    cut: { constructor: ClipboardEvent, processParameters: onlyBubble },
    copy: { constructor: ClipboardEvent, processParameters: onlyBubble },
    paste: { constructor: ClipboardEvent, processParameters: onlyBubble },
    keydown: { constructor: KeyboardEvent, processParameters: keyboardEventBubble },
    keypress: { constructor: KeyboardEvent, processParameters: keyboardEventBubble },
    keyup: { constructor: KeyboardEvent, processParameters: keyboardEventBubble },
    drag: { constructor: DragEvent, processParameters: onlyBubble },
    dragend: { constructor: DragEvent, processParameters: onlyBubble },
    dragenter: { constructor: DragEvent, processParameters: onlyBubble },
    dragstart: { constructor: DragEvent, processParameters: onlyBubble },
    dragleave: { constructor: DragEvent, processParameters: onlyBubble },
    dragover: { constructor: DragEvent, processParameters: onlyBubble },
    drop: { constructor: DragEvent, processParameters: onlyBubble },
    input: { constructor: InputEvent, processParameters: onlyBubble },
    compositionstart: { constructor: CompositionEvent, processParameters: onlyBubble },
    compositionend: { constructor: CompositionEvent, processParameters: onlyBubble },
};

export async function triggerEvent(el, selector, eventType, eventAttrs = {}) {
    let event;
    if (eventType in EVENT_TYPES) {
        const { constructor, processParameters } = EVENT_TYPES[eventType];
        event = new constructor(eventType, processParameters(eventAttrs));
    } else {
        event = new Event(eventType, Object.assign({}, eventAttrs, { bubbles: true }));
    }
    const target = findElement(el, selector);
    target.dispatchEvent(event);
    await nextTick();
}

export async function triggerEvents(el, querySelector, events) {
    for (let e = 0; e < events.length; e++) {
        await triggerEvent(el, querySelector, events[e]);
    }
}

export function click(el, selector) {
    return triggerEvent(el, selector, "click", { bubbles: true, cancelable: true });
}

/**
 * Triggers an hotkey properly disregarding the operating system.
 *
 * @param {string} hotkey
 * @param {boolean} altIsOptional
 * @param {KeyboardEventInit} eventAttrs
 */
export function triggerHotkey(hotkey, altIsOptional = false, eventAttrs = {}) {
    eventAttrs.key = hotkey.split("+").pop();

    if (/shift/i.test(hotkey)) {
        eventAttrs.shiftKey = true;
    }

    if (/control/i.test(hotkey)) {
        if (isMacOS()) {
            eventAttrs.metaKey = true;
        } else {
            eventAttrs.ctrlKey = true;
        }
    }

    if (!altIsOptional) {
        if (isMacOS()) {
            eventAttrs.ctrlKey = true;
        } else {
            eventAttrs.altKey = true;
        }
    }

    window.dispatchEvent(new KeyboardEvent("keydown", eventAttrs));
}

export async function legacyExtraNextTick() {
    return nextTick();
}

export function mockDownload(cb) {
    patchWithCleanup(download, { _download: cb });
}
