/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { isMacOS } from "@web/core/browser/feature_detection";
import { patch, unpatch } from "@web/core/utils/patch";
import { registerCleanup } from "./cleanup";
import { download } from "@web/core/network/download";

const { App, onMounted, onPatched, useComponent } = owl;

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
    const originalZone = luxon.Settings.defaultZone;
    luxon.Settings.defaultZone = new luxon.FixedOffsetZone.instance(offset);
    registerCleanup(() => {
        luxon.Settings.defaultZone = originalZone;
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

/**
 * @returns {HTMLElement}
 */
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
    /** @type {(value:any)=>void} */
    let resolve;
    /** @type {(reason?:any)=>void} */
    let reject;
    const prom = new Promise((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return Object.assign(prom, { resolve, reject });
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

const mouseEventMapping = (args) => ({
    clientX: args ? args.pageX : undefined,
    clientY: args ? args.pageY : undefined,
    ...args,
    bubbles: true,
    cancelable: true,
    view: window,
});

const mouseEventNoBubble = (args) => ({
    clientX: args ? args.pageX : undefined,
    clientY: args ? args.pageY : undefined,
    ...args,
    bubbles: false,
    cancelable: false,
    view: window,
});

const touchEventMapping = (args) => ({
    ...args,
    bubbles: true,
    cancelable: true,
    touches: args.touches ? [...args.touches.map((e) => new Touch(e))] : undefined,
});

const touchEventCancelMapping = (args) => ({
    ...touchEventMapping(args),
    cancelable: false,
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

if (typeof TouchEvent === "function") {
    Object.assign(EVENT_TYPES, {
        touchstart: { constructor: TouchEvent, processParameters: touchEventMapping },
        touchend: { constructor: TouchEvent, processParameters: touchEventMapping },
        touchmove: { constructor: TouchEvent, processParameters: touchEventMapping },
        touchcancel: { constructor: TouchEvent, processParameters: touchEventCancelMapping },
    });
}

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
        if (Array.isArray(events[e])) {
            await triggerEvent(el, querySelector, events[e][0], events[e][1]);
        } else {
            await triggerEvent(el, querySelector, events[e]);
        }
    }
}

/**
 * Triggers a scroll event on the given target
 *
 * If the target cannot be scrolled or an axis has reached
 * the end of the scrollable area, the event can be transmitted
 * to its nearest parent until it can be triggered
 *
 * @param {HTMLElement} target target of the scroll event
 * @param {Object} coordinates
 * @param {Number} coordinates[left] coordinates to scroll horizontally
 * @param {Number} coordinates[top] coordinates to scroll vertically
 * @param {Boolean} canPropagate states if the scroll can propagate to a scrollable parent
 */
export async function triggerScroll(
    target,
    coordinates = { left: null, top: null },
    canPropagate = true
) {
    const isScrollable =
        (target.scrollHeight > target.clientHeight && target.clientHeight > 0) ||
        (target.scrollWidth > target.clientWidth && target.clientWidth > 0);
    if (!isScrollable && !canPropagate) return;
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
        target.dispatchEvent(new UIEvent("scroll"));
        if (!canPropagate || !Object.entries(coordinates).length) return;
    }
    target.parentElement
        ? triggerScroll(target.parentElement, coordinates)
        : window.dispatchEvent(new UIEvent("scroll"));
    await nextTick();
}

export function click(el, selector) {
    return triggerEvent(el, selector, "click", { bubbles: true, cancelable: true });
}

export function clickEdit(htmlElement) {
    if (htmlElement.querySelectorAll(".o_form_button_edit").length) {
        return click(htmlElement, ".o_form_button_edit");
    } else if (htmlElement.querySelectorAll(".o_list_button_edit").length) {
        return click(htmlElement, ".o_list_button_edit");
    } else {
        throw new Error("No edit button found to be clicked.");
    }
}

export function clickSave(htmlElement) {
    if (htmlElement.querySelectorAll(".o_form_button_save").length) {
        return click(htmlElement, ".o_form_button_save");
    } else if (htmlElement.querySelectorAll(".o_list_button_save").length) {
        return click(htmlElement, ".o_list_button_save");
    } else {
        throw new Error("No save button found to be clicked.");
    }
}

export async function mouseEnter(el, selector) {
    return triggerEvent(el, selector, "mouseenter");
}

export async function editInput(el, selector, value) {
    const input = findElement(el, selector);
    input.value = value;
    await triggerEvent(input, null, "input");
    return triggerEvent(input, null, "change");
}

export function editSelect(el, selector, value) {
    const select = findElement(el, selector);
    select.value = value;
    return triggerEvent(select, null, "change");
}

/**
 * Triggers an hotkey properly disregarding the operating system.
 *
 * @param {string} hotkey
 * @param {boolean} addOverlayModParts
 * @param {KeyboardEventInit} eventAttrs
 */
export function triggerHotkey(hotkey, addOverlayModParts = false, eventAttrs = {}) {
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

    document.activeElement.dispatchEvent(new KeyboardEvent("keydown", eventAttrs));
    document.activeElement.dispatchEvent(new KeyboardEvent("keyup", eventAttrs));
}

export async function legacyExtraNextTick() {
    return nextTick();
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
    let id = 1;
    patchWithCleanup(browser, {
        requestAnimationFrame(fn) {
            callbacks.set(id, fn);
            return id++;
        },
        cancelAnimationFrame(id) {
            callbacks.delete(id);
        },
    });
    return function execRegisteredCallbacks() {
        for (const fn of callbacks.values()) {
            fn();
        }
        callbacks.clear();
    };
}

export async function mount(Comp, target, config = {}) {
    let { props, env } = config;
    env = env || {};
    const configuration = {
        env,
        templates: window.__OWL_TEMPLATES__,
        test: true,
        props,
    };
    if (env.services && "localization" in env.services) {
        configuration.translateFn = env._t;
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

const lifeCycleHooks = [
    "onError",
    "onMounted",
    "onPatched",
    "onRendered",
    "onWillDestroy",
    "onWillPatch",
    "onWillRender",
    "onWillStart",
    "onWillUnmount",
    "onWillUpdateProps",
];
export function useLogLifeCycle(logFn, name = "") {
    const component = owl.useComponent();
    let loggedName = `${component.constructor.name}`;
    if (name) {
        loggedName = `${component.constructor.name} ${name}`;
    }
    for (const hook of lifeCycleHooks) {
        owl[hook](() => {
            logFn(`${hook} ${loggedName}`);
        });
    }
}

/**
 * Returns the list of nodes containing n2 (included) that do not contain n1.
 *
 * @param {Node} n1
 * @param {Node} n2
 * @returns {Node[]}
 */
const getDifferentParents = (n1, n2) => {
    const parents = [n2];
    while (parents[0].parentNode) {
        const parent = parents[0].parentNode;
        if (parent.contains(n1)) {
            break;
        }
        parents.unshift(parent);
    }
    return parents;
};

/**
 * Helper performing a drag and drop sequence.
 *
 * - the 'fromSelector' is used to determine the element on which the drag will
 *  start;
 * - the 'toSelector' will determine the element on which the first one will be
 * dropped.
 *
 * The first element will be dragged by its center, and will be dropped on the
 * bottom-right inner pixel of the target element. This behavior covers both
 * cases of appending the first element to the end of a list (toSelector =
 * target list) or moving it at the position of another element, effectively
 * placing the first element before the second (toSelector = other element).
 *
 * Note that only the last event is awaited, since all the others are
 * considered to be synchronous.
 *
 * @param {string} fromSelector
 * @param {string} toSelector
 * @returns {Promise<void>}
 */
export const dragAndDrop = async (fromSelector, toSelector) => {
    const fixture = getFixture();
    const from = fixture.querySelector(fromSelector);
    const to = fixture.querySelector(toSelector);

    // Mouse down on main target then move to a far away position to initiate the drag
    const fromRect = from.getBoundingClientRect();
    triggerEvent(from, null, "mousedown", {
        clientX: fromRect.x + fromRect.width / 2,
        clientY: fromRect.y + fromRect.height / 2,
    });
    triggerEvent(window, null, "mousemove", { clientX: -999, clientY: -999 });

    // Find target position
    const toRect = to.getBoundingClientRect();
    const toPos = {
        clientX: toRect.x + toRect.width - 1,
        clientY: toRect.y + toRect.height - 1,
    };

    // Move, enter and drop the element on the target
    triggerEvent(window, null, "mousemove", toPos);
    // "mouseenter" is fired on every parent of `to` that do not contain
    // `from` (typically: different parent lists).
    for (const target of getDifferentParents(from, to)) {
        triggerEvent(target, null, "mouseenter", toPos);
    }
    triggerEvent(from, null, "mouseup", toPos);
    await triggerEvent(from, null, "click", toPos);
};
