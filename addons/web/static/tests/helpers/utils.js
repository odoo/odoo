/** @odoo-module **/

import { templates } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { isMacOS } from "@web/core/browser/feature_detection";
import { download } from "@web/core/network/download";
import { Deferred } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { isVisible } from "@web/core/utils/ui";
import { _t } from "@web/core/l10n/translation";
import { registerCleanup } from "./cleanup";

import {
    App,
    onError,
    onMounted,
    onPatched,
    onRendered,
    onWillDestroy,
    onWillPatch,
    onWillRender,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
    useComponent,
} from "@odoo/owl";

/**
 * @typedef {keyof HTMLElementEventMap | keyof WindowEventMap} EventType
 *
 * @typedef {Side | `${Side}-${Side}` | { x?: number, y?: number }} Position
 *
 * @typedef {"bottom" | "left" | "right" | "top"} Side
 *
 * @typedef TriggerEventOptions
 * @property {boolean} [skipVisibilityCheck=false]
 * @property {boolean} [sync=false]
 */

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
    var RealDate = window.Date;
    var actualDate = new RealDate();

    // By default, RealDate uses the browser offset, so we must replace it with the offset fixed in luxon.
    var fakeDate = new RealDate(year, month, day, hours, minutes, seconds);
    if (!(luxon.Settings.defaultZone instanceof luxon.FixedOffsetZone)) {
        throw new Error("luxon.Settings.defaultZone must be a FixedOffsetZone");
    }
    const browserOffset = -fakeDate.getTimezoneOffset();
    const patchedOffset = luxon.Settings.defaultZone.offset();
    const offsetDiff = patchedOffset - browserOffset;
    const correctedMinutes = fakeDate.getMinutes() - offsetDiff;
    fakeDate.setMinutes(correctedMinutes);

    var timeInterval = actualDate.getTime() - fakeDate.getTime();

    // eslint-disable-next-line no-global-assign
    window.Date = (function (NativeDate) {
        function Date(Y, M, D, h, m, s, ms) {
            var length = arguments.length;
            let date;
            if (arguments.length > 0) {
                date =
                    length == 1 && String(Y) === Y // isString(Y)
                        ? // We explicitly pass it through parse:
                          new NativeDate(Date.parse(Y))
                        : // We have to manually make calls depending on argument
                        // length here
                        length >= 7
                        ? new NativeDate(Y, M, D, h, m, s, ms)
                        : length >= 6
                        ? new NativeDate(Y, M, D, h, m, s)
                        : length >= 5
                        ? new NativeDate(Y, M, D, h, m)
                        : length >= 4
                        ? new NativeDate(Y, M, D, h)
                        : length >= 3
                        ? new NativeDate(Y, M, D)
                        : length >= 2
                        ? new NativeDate(Y, M)
                        : length >= 1
                        ? new NativeDate(Y)
                        : new NativeDate();
                // Prevent mixups with unfixed Date object
                date.constructor = Date;
                return date;
            } else {
                date = new NativeDate();
                var time = date.getTime();
                time -= timeInterval;
                date.setTime(time);
                return date;
            }
        }

        // Copy any custom methods a 3rd party library may have added
        for (var key in NativeDate) {
            Date[key] = NativeDate[key];
        }

        // Copy "native" methods explicitly; they may be non-enumerable
        // exception: 'now' uses fake date as reference
        Date.now = function () {
            var date = new NativeDate();
            var time = date.getTime();
            time -= timeInterval;
            return time;
        };
        Date.UTC = NativeDate.UTC;
        Date.prototype = NativeDate.prototype;
        Date.prototype.constructor = Date;

        // Upgrade Date.parse to handle simplified ISO 8601 strings
        Date.parse = NativeDate.parse;
        return Date;
    })(Date);

    registerCleanup(() => {
        window.Date = RealDate;
    });
}

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

export function findElement(el, selector) {
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

/**
 * Triggers a scroll event on the given target
 *
 * If the target cannot be scrolled or an axis has reached
 * the end of the scrollable area, the event can be transmitted
 * to its nearest parent until it can be triggered
 *
 * @param {Element} target target of the scroll event
 * @param {Object} coordinates
 * @param {number} coordinates.left coordinates to scroll horizontally
 * @param {number} coordinates.top coordinates to scroll vertically
 * @param {boolean} canPropagate states if the scroll can propagate to a scrollable parent
 */
export async function triggerScroll(
    target,
    coordinates = { left: null, top: null },
    canPropagate = true
) {
    const isScrollable =
        (target.scrollHeight > target.clientHeight && target.clientHeight > 0) ||
        (target.scrollWidth > target.clientWidth && target.clientWidth > 0);
    if (!isScrollable && !canPropagate) {
        return;
    }
    if (isScrollable) {
        const canScrollFrom = {
            left:
                coordinates.left > target.scrollLeft
                    ? target.scrollLeft + target.clientWidth < target.scrollWidth
                    : target.scrollLeft > 0,
            top:
                coordinates.top > target.scrollTop
                    ? target.scrollTop + target.clientHeight < target.scrollHeight
                    : target.scrollTop > 0,
        };
        const scrollCoordinates = {};
        Object.entries(coordinates).forEach(([key, value]) => {
            if (value !== null && canScrollFrom[key]) {
                scrollCoordinates[key] = value;
                delete coordinates[key];
            }
        });
        target.scrollTo(scrollCoordinates);
        await triggerEvent(target, null, "scroll");
        if (!canPropagate || !Object.entries(coordinates).length) {
            return;
        }
    }
    target.parentElement
        ? triggerScroll(target.parentElement, coordinates)
        : triggerEvent(window, null, "scroll");
    await nextTick();
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
        ["pointerdown", "mousedown", "focus", "pointerup", "mouseup", ["click", mouseEventInit]],
        { skipVisibilityCheck }
    );
}

export function clickCreate(htmlElement) {
    if (
        htmlElement.querySelectorAll(
            ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_form_button_create"
        ).length
    ) {
        return click(
            htmlElement,
            ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_form_button_create"
        );
    } else if (
        htmlElement.querySelectorAll(
            ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_list_button_create"
        ).length
    ) {
        return click(
            htmlElement,
            ".o_control_panel_main_buttons .d-none.d-xl-inline-flex .o_list_button_create"
        );
    } else {
        throw new Error("No edit button found to be clicked.");
    }
}

export function clickEdit(htmlElement) {
    if (htmlElement.querySelectorAll(".o_list_button_edit").length) {
        return click(htmlElement, ".o_list_button_edit");
    } else {
        throw new Error("No edit button found to be clicked.");
    }
}

export async function clickSave(htmlElement) {
    if (htmlElement.querySelectorAll(".o_form_status_indicator").length) {
        await mouseEnter(htmlElement, ".o_form_status_indicator");
    }
    if (htmlElement.querySelectorAll(".o_form_button_save").length) {
        return click(htmlElement, ".o_form_button_save");
    }
    const listSaveButtons = htmlElement.querySelectorAll(".o_list_button_save");
    if (listSaveButtons.length) {
        return listSaveButtons.length >= 2 ? click(listSaveButtons[1]) : click(listSaveButtons[0]);
    } else {
        throw new Error("No save button found to be clicked.");
    }
}

export async function clickDiscard(htmlElement) {
    if (htmlElement.querySelectorAll(".o_form_status_indicator").length) {
        await mouseEnter(htmlElement, ".o_form_status_indicator");
    }
    if (htmlElement.querySelectorAll(".o_form_button_cancel").length) {
        return click(htmlElement, ".o_form_button_cancel");
    } else if ($(htmlElement).find(".o_list_button_discard:visible").length) {
        return click($(htmlElement).find(".o_list_button_discard:visible").get(0));
    } else {
        throw new Error("No discard button found to be clicked.");
    }
}

/**
 * Trigger pointerenter and mouseenter events on the given target. If no
 * coordinates are given, the event is located by default
 * in the middle of the target to simplify the test process
 *
 * @param {Element} el
 * @param {string} selector
 * @param {Object} coordinates position of the mouseenter event
 */
export async function mouseEnter(el, selector, coordinates) {
    const target = el.querySelector(selector) || el;
    const atPos = coordinates || {
        clientX: target.getBoundingClientRect().left + target.getBoundingClientRect().width / 2,
        clientY: target.getBoundingClientRect().top + target.getBoundingClientRect().height / 2,
    };
    return triggerEvents(target, null, ["pointerenter", "mouseenter"], atPos);
}

/**
 * Trigger pointerleave and mouseleave events on the given target.
 *
 * @param {Element} el
 * @param {string} selector
 */
export async function mouseLeave(el, selector) {
    const target = el.querySelector(selector) || el;
    return triggerEvents(target, null, ["pointerleave", "mouseleave"]);
}

export async function editInput(el, selector, value) {
    const input = findElement(el, selector);
    if (!(input instanceof HTMLInputElement || input instanceof HTMLTextAreaElement)) {
        throw new Error("Only 'input' and 'textarea' elements can be edited with 'editInput'.");
    }
    if (
        !["text", "textarea", "email", "search", "color", "number", "file", "tel"].includes(
            input.type
        )
    ) {
        throw new Error(`Type "${input.type}" not supported by 'editInput'.`);
    }

    const eventOpts = {};
    if (input.type === "file") {
        const files = Array.isArray(value) ? value : [value];
        const dataTransfer = new DataTransfer();
        for (const file of files) {
            if (!(file instanceof File)) {
                throw new Error(`File input value should be one or several File objects.`);
            }
            dataTransfer.items.add(file);
        }
        input.files = dataTransfer.files;
        eventOpts.skipVisibilityCheck = true;
    } else {
        input.value = value;
    }

    await triggerEvents(input, null, ["input", "change"], eventOpts);

    if (input.type === "file") {
        // Need to wait for the file to be loaded by the input
        await nextTick();
        await nextTick();
    }
}

export function editSelect(el, selector, value) {
    const select = findElement(el, selector);
    if (select.tagName !== "SELECT") {
        throw new Error("Only select tag can be edited with selectInput.");
    }
    select.value = value;
    return triggerEvent(select, null, "change");
}

export async function editSelectMenu(el, selector, value) {
    const dropdown = el.querySelector(selector);
    await click(dropdown.querySelector(".dropdown-toggle"));
    for (const item of Array.from(dropdown.querySelectorAll(".dropdown-item"))) {
        if (item.textContent === value) {
            return click(item);
        }
    }
}

/**
 * Triggers an hotkey properly disregarding the operating system.
 *
 * @param {string} hotkey
 * @param {boolean} addOverlayModParts
 * @param {KeyboardEventInit} eventAttrs
 */
export async function triggerHotkey(hotkey, addOverlayModParts = false, eventAttrs = {}) {
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

    if (/alt/i.test(hotkey) || addOverlayModParts) {
        if (isMacOS()) {
            eventAttrs.ctrlKey = true;
        } else {
            eventAttrs.altKey = true;
        }
    }

    if (!("bubbles" in eventAttrs)) {
        eventAttrs.bubbles = true;
    }

    const [keydownEvent, keyupEvent] = await triggerEvents(
        document.activeElement,
        null,
        [
            ["keydown", eventAttrs],
            ["keyup", eventAttrs],
        ],
        { skipVisibilityCheck: true }
    );

    return { keydownEvent, keyupEvent };
}

export function mockDownload(cb) {
    patchWithCleanup(download, { _download: cb });
}

export const hushConsole = Object.create(null);
for (const propName of Object.keys(window.console)) {
    hushConsole[propName] = () => {};
}

export function mockTimeout() {
    const timeouts = new Map();
    let currentTime = 0;
    let id = 1;
    patchWithCleanup(browser, {
        setTimeout(fn, delay = 0) {
            timeouts.set(id, { fn, scheduledFor: delay + currentTime, id });
            return id++;
        },
        clearTimeout(id) {
            timeouts.delete(id);
        },
    });
    return {
        execRegisteredTimeouts() {
            for (const { fn } of timeouts.values()) {
                fn();
            }
            timeouts.clear();
        },
        async advanceTime(duration) {
            // wait here so all microtasktick scheduled in this frame can be
            // executed and possibly register their own timeout
            await nextTick();
            currentTime += duration;
            for (const { fn, scheduledFor, id } of timeouts.values()) {
                if (scheduledFor <= currentTime) {
                    fn();
                    timeouts.delete(id);
                }
            }
            // wait here to make sure owl can update the UI
            await nextTick();
        },
    };
}

export function mockAnimationFrame() {
    const callbacks = new Map();
    let currentTime = 0;
    let id = 1;
    patchWithCleanup(browser, {
        requestAnimationFrame(fn) {
            callbacks.set(id, { fn, scheduledFor: 16 + currentTime, id });
            return id++;
        },
        cancelAnimationFrame(id) {
            callbacks.delete(id);
        },
        performance: { now: () => currentTime },
    });
    return {
        execRegisteredAnimationFrames() {
            for (const { fn } of callbacks.values()) {
                fn(currentTime);
            }
            callbacks.clear();
        },
        async advanceFrame(count = 1) {
            // wait here so all microtasktick scheduled in this frame can be
            // executed and possibly register their own timeout
            await nextTick();
            currentTime += 16 * count;
            for (const { fn, scheduledFor, id } of callbacks.values()) {
                if (scheduledFor <= currentTime) {
                    fn(currentTime);
                    callbacks.delete(id);
                }
            }
            // wait here to make sure owl can update the UI
            await nextTick();
        },
    };
}

export async function mount(Comp, target, config = {}) {
    let { props, env } = config;
    env = env || {};
    const configuration = {
        env,
        templates,
        test: true,
        props,
    };
    if (env.services && "localization" in env.services) {
        configuration.translateFn = _t;
    }
    const app = new App(Comp, configuration);
    registerCleanup(() => app.destroy());
    return app.mount(target);
}

export function destroy(comp) {
    comp.__owl__.app.destroy();
}

export function findChildren(comp, predicate = (e) => e) {
    const queue = [];
    [].unshift.apply(queue, Object.values(comp.__owl__.children));

    while (queue.length > 0) {
        const curNode = queue.pop();
        if (predicate(curNode)) {
            return curNode;
        }
        [].unshift.apply(queue, Object.values(curNode.component.__owl__.children));
    }
}

// partial replacement of t-ref on component
export function useChild() {
    const node = useComponent().__owl__;
    const setChild = () => {
        const componentNode = Object.values(node.children)[0];
        node.component.child = componentNode.component;
    };
    onMounted(setChild);
    onPatched(setChild);
}

export function useLogLifeCycle(logFn, name = "") {
    const component = useComponent();
    let loggedName = `${component.constructor.name}`;
    if (name) {
        loggedName = `${component.constructor.name} ${name}`;
    }
    onError(() => {
        logFn(`onError ${loggedName}`);
    });
    onMounted(() => {
        logFn(`onMounted ${loggedName}`);
    });
    onPatched(() => {
        logFn(`onPatched ${loggedName}`);
    });
    onRendered(() => {
        logFn(`onRendered ${loggedName}`);
    });
    onWillDestroy(() => {
        logFn(`onWillDestroy ${loggedName}`);
    });
    onWillPatch(() => {
        logFn(`onWillPatch ${loggedName}`);
    });
    onWillRender(() => {
        logFn(`onWillRender ${loggedName}`);
    });
    onWillStart(() => {
        logFn(`onWillStart ${loggedName}`);
    });
    onWillUnmount(() => {
        logFn(`onWillUnmount ${loggedName}`);
    });
    onWillUpdateProps(() => {
        logFn(`onWillUpdateProps ${loggedName}`);
    });
}

/**
 * Returns the list of nodes containing n2 (included) that do not contain n1.
 *
 * @param {Node} n1
 * @param {Node} n2
 * @returns {Node[]}
 */
function getDifferentParents(n1, n2) {
    const parents = [n2];
    while (parents[0].parentNode) {
        const parent = parents[0].parentNode;
        if (parent.contains(n1)) {
            break;
        }
        parents.unshift(parent);
    }
    return parents;
}

/**
 * Helper performing a drag and drop sequence.
 *
 * - 'from' is used to determine the element on which the drag will start;
 * - 'target' will determine the element on which the first one will be dropped.
 *
 * The first element will be dragged by its center, and will be dropped on the
 * bottom-right inner pixel of the target element. This behavior covers both
 * cases of appending the first element to the end of a list (toSelector =
 * target list) or moving it at the position of another element, effectively
 * placing the first element before the second (toSelector = other element).
 *
 * A position can be given to drop the first element above, below, or on the
 * side of the second (default is inside, as specified above).
 *
 * Note that only the last event is awaited, since all the others are
 * considered to be synchronous.
 *
 * @param {Element | string} from
 * @param {Element | string} to
 * @param {Position} [position]
 */
export async function dragAndDrop(from, to, position) {
    const { drop } = await drag(from);
    await drop(to, position);
}

/**
 * Helper performing a drag.
 *
 * - the 'from' selector is used to determine the element on which the drag will
 *  start;
 * - the 'target' selector will determine the element on which the dragged element will be
 * moved.
 *
 * Returns a drop function
 *
 * @param {Element | string} from
 */
export async function drag(from, pointerType = "mouse") {
    const assertIsDragging = (fn, endDrag) => {
        return {
            async [fn.name](...args) {
                if (dragEndReason) {
                    throw new Error(
                        `Cannot execute drag helper '${fn.name}': drag sequence has been ended by '${dragEndReason}'.`
                    );
                }
                await fn(...args);
                if (endDrag) {
                    dragEndReason = fn.name;
                }
            },
        }[fn.name];
    };

    const cancel = assertIsDragging(async function cancel() {
        await triggerEvent(window, null, "keydown", { key: "Escape" });
    }, true);

    /**
     * @param {Element | string} [to]
     * @param {Position} [position]
     */
    const drop = assertIsDragging(async function drop(to, position) {
        if (to) {
            await moveTo(to, position);
        }
        await triggerEvent(target || source, null, "pointerup", targetPosition);
    }, true);

    /**
     * @param {Element | string} selector
     */
    const getEl = (selector) =>
        selector instanceof Element ? selector : fixture.querySelector(selector);

    /**
     * @param {Position} [position]
     */
    const getTargetPosition = (position) => {
        const tRect = target.getBoundingClientRect();
        const tPos = {
            clientX: Math.floor(tRect.x),
            clientY: Math.floor(tRect.y),
        };
        if (position && typeof position === "object") {
            // x and y coordinates start from the element's initial coordinates
            tPos.clientX += position.x || 0;
            tPos.clientY += position.y || 0;
        } else {
            const positions = typeof position === "string" ? position.split("-") : [];

            // X position
            if (positions.includes("left")) {
                tPos.clientX -= 1;
            } else if (positions.includes("right")) {
                tPos.clientX += Math.ceil(tRect.width) + 1;
            } else {
                tPos.clientX += Math.floor(tRect.width / 2);
            }

            // Y position
            if (positions.includes("top")) {
                tPos.clientY -= 1;
            } else if (positions.includes("bottom")) {
                tPos.clientY += Math.ceil(tRect.height) + 1;
            } else {
                tPos.clientY += Math.floor(tRect.height / 2);
            }
        }
        return tPos;
    };

    /**
     * @param {Element | string} [to]
     * @param {Position} [position]
     */
    const moveTo = assertIsDragging(async function moveTo(to, position) {
        target = getEl(to);
        if (!target) {
            return;
        }

        // Recompute target position
        targetPosition = getTargetPosition(position);

        // Move, enter and drop the element on the target
        await triggerEvent(source, null, "pointermove", targetPosition);

        // "pointerenter" is fired on every parent of `target` that do not contain
        // `from` (typically: different parent lists).
        for (const parent of getDifferentParents(source, target)) {
            triggerEvent(parent, null, "pointerenter", targetPosition);
        }
        await nextTick();

        return dragHelpers;
    }, false);

    const dragHelpers = { cancel, drop, moveTo };
    const fixture = getFixture();

    const source = getEl(from instanceof Element ? from : fixture.querySelector(from));
    const sourceRect = source.getBoundingClientRect();

    let dragEndReason = null;
    let target;
    let targetPosition;

    // Pointer down on main target
    await triggerEvent(source, null, "pointerdown", {
        pointerType,
        clientX: sourceRect.x + sourceRect.width / 2,
        clientY: sourceRect.y + sourceRect.height / 2,
    });

    return dragHelpers;
}

export async function clickDropdown(target, fieldName) {
    const dropdownInput = target.querySelector(`[name='${fieldName}'] .dropdown input`);
    dropdownInput.focus();
    await nextTick();
    await click(dropdownInput);
}

export async function clickOpenedDropdownItem(target, fieldName, itemContent) {
    const dropdownItems = target.querySelectorAll(`[name='${fieldName}'] .dropdown ul li`);
    const indexToClick = Array.from(dropdownItems)
        .map((html) => html.textContent)
        .indexOf(itemContent);
    if (indexToClick === -1) {
        throw new Error(`The element '${itemContent}' does not exist in the dropdown`);
    }
    await click(dropdownItems[indexToClick]);
}

export async function selectDropdownItem(target, fieldName, itemContent) {
    await clickDropdown(target, fieldName);
    await clickOpenedDropdownItem(target, fieldName, itemContent);
}

export function getNodesTextContent(nodes) {
    return Array.from(nodes).map((n) => n.textContent);
}

/**
 * Click to open the dropdown on a many2one
 */
export async function clickOpenM2ODropdown(el, fieldName, selector) {
    const m2oSelector = `${selector || ""} .o_field_many2one[name=${fieldName}] input`;
    const matches = el.querySelectorAll(m2oSelector);
    if (matches.length !== 1) {
        throw new Error(
            `cannot open m2o: selector ${selector} has been found ${matches.length} instead of 1`
        );
    }

    await click(matches[0]);
    return matches[0];
}

/**
 * Click on the active (highlighted) selection in a m2o dropdown.
 */
// TO FIX
export async function clickM2OHighlightedItem(el, fieldName, selector) {
    const m2oSelector = `${selector || ""} .o_field_many2one[name=${fieldName}] input`;
    // const $dropdown = $(m2oSelector).autocomplete('widget');
    const matches = el.querySelectorAll(m2oSelector);
    if (matches.length !== 1) {
        throw new Error(
            `cannot open m2o: selector ${selector} has been found ${matches.length} instead of 1`
        );
    }
    // clicking on an li (no matter which one), will select the focussed one
    return click(matches[0].parentElement.querySelector("li"));
}

// X2Many
export async function addRow(target, selector) {
    await click(target.querySelector(`${selector ? selector : ""} .o_field_x2many_list_row_add a`));
}

export async function removeRow(target, index) {
    await click(target.querySelectorAll(".o_list_record_remove")[index]);
}
