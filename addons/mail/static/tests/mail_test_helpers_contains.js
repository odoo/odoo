/** @odoo-module alias=@web/../tests/utils default=false */

import { __debug__, after, afterEach, expect, getFixture } from "@odoo/hoot";
import { queryAll, queryFirst } from "@odoo/hoot-dom";
import { Deferred, tick } from "@odoo/hoot-mock";
import { isMacOS } from "@web/core/browser/feature_detection";
import { isVisible } from "@web/core/utils/ui";

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

/**
 * @template {EventType} T
 * @param {Element} el
 * @param {string | null | undefined | false} selector
 * @param {T} eventType
 * @param {EventInit} [eventInit]
 * @param {TriggerEventOptions} [options={}]
 * @returns {GlobalEventHandlersEventMap[T] | Promise<GlobalEventHandlersEventMap[T]>}
 */
function triggerEvent(el, selector, eventType, eventInit, options = {}) {
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

    if (__debug__.debug) {
        const group = `%c[${event.type.toUpperCase()}]`;
        console.groupCollapsed(group, "color: #b52c9b");
        console.log(target, event);
        console.groupEnd(group, "color: #b52c9b");
    }

    if (options.sync) {
        return event;
    } else {
        return tick().then(() => event);
    }
}

/**
 * @param {Element} el
 * @param {string | null | undefined | false} selector
 * @param {(EventType | [EventType, EventInit])[]} [eventDefs]
 * @param {TriggerEventOptions} [options={}]
 */
function _triggerEvents(el, selector, eventDefs, options = {}) {
    const events = [...eventDefs].map((eventDef) => {
        const [eventType, eventInit] = Array.isArray(eventDef) ? eventDef : [eventDef, {}];
        return triggerEvent(el, selector, eventType, eventInit, options);
    });
    if (options.sync) {
        return events;
    } else {
        return tick().then(() => events);
    }
}

function _click(
    el,
    selector,
    { mouseEventInit = {}, skipDisabledCheck = false, skipVisibilityCheck = false } = {}
) {
    if (!skipDisabledCheck && el.disabled) {
        throw new Error("Can't click on a disabled button");
    }
    return _triggerEvents(
        el,
        selector,
        ["pointerdown", "mousedown", "focus", "pointerup", "mouseup", ["click", mouseEventInit]],
        { skipVisibilityCheck }
    );
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

    await _triggerEvents(input, null, ["input", "change"], eventOpts);

    if (input.type === "file") {
        // Need to wait for the file to be loaded by the input
        await tick();
        await tick();
    }
}

/**
 * Create a fake object 'dataTransfer', linked to some files,
 * which is passed to drag and drop events.
 *
 * @param {Object[]} files
 * @returns {Object}
 */
function createFakeDataTransfer(files) {
    return {
        dropEffect: "all",
        effectAllowed: "all",
        files,
        items: [],
        types: ["Files"],
    };
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then clicks on it.
 *
 * @param {string} selector
 * @param {ContainsOptions} [options] forwarded to `contains`
 * @param {boolean} [options.shiftKey]
 */
export async function click(selector, options = {}) {
    const { shiftKey } = options;
    delete options.shiftKey;
    await contains(selector, { click: { shiftKey }, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then dragenters `files` on it.
 *
 * @param {string} selector
 * @param {Object[]} files
 * @param {ContainsOptions} [options] forwarded to `contains`
 */
export async function dragenterFiles(selector, files, options) {
    await contains(selector, { dragenterFiles: files, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then dragovers `files` on it.
 *
 * @param {string} selector
 * @param {Object[]} files
 * @param {ContainsOptions} [options] forwarded to `contains`
 */
export async function dragoverFiles(selector, files, options) {
    await contains(selector, { dragoverFiles: files, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then drops `files` on it.
 *
 * @param {string} selector
 * @param {Object[]} files
 * @param {ContainsOptions} [options] forwarded to `contains`
 */
export async function dropFiles(selector, files, options) {
    await contains(selector, { dropFiles: files, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then inputs `files` on it.
 *
 * @param {string} selector
 * @param {Object[]} files
 * @param {ContainsOptions} [options] forwarded to `contains`
 */
export async function inputFiles(selector, files, options) {
    await contains(selector, { inputFiles: files, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then pastes `files` on it.
 *
 * @param {string} selector
 * @param {Object[]} files
 * @param {ContainsOptions} [options] forwarded to `contains`
 */
export async function pasteFiles(selector, files, options) {
    await contains(selector, { pasteFiles: files, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then focuses on it.
 *
 * @param {string} selector
 * @param {ContainsOptions} [options] forwarded to `contains`
 */
export async function focus(selector, options) {
    await contains(selector, { setFocus: true, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then inserts the given `content`.
 *
 * @param {string} selector
 * @param {string} content
 * @param {ContainsOptions} [options] forwarded to `contains`
 * @param {boolean} [options.replace=false]
 */
export async function insertText(selector, content, options = {}) {
    const { replace = false } = options;
    delete options.replace;
    await contains(selector, { ...options, insertText: { content, replace } });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then sets its `scrollTop` to the given value.
 *
 * @param {string} selector
 * @param {number|"bottom"} scrollTop
 * @param {ContainsOptions} [options] forwarded to `contains`
 */
export async function scroll(selector, scrollTop, options) {
    await contains(selector, { setScroll: scrollTop, ...options });
}

/**
 * Waits until exactly one element matching the given `selector` is present in
 * `options.target` and then triggers `event` on it.
 *
 * @param {string} selector
 * @param {(import("@web/../tests/helpers/utils").EventType|[import("@web/../tests/helpers/utils").EventType, EventInit])[]} events
 * @param {ContainsOptions} [options] forwarded to `contains`
 */
export async function triggerEvents(selector, events, options) {
    await contains(selector, { triggerEvents: events, ...options });
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
    const [keydownEvent, keyupEvent] = await _triggerEvents(
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

function log(ok, message) {
    expect(Boolean(ok)).toBe(true, { message });
}

let hasUsedContainsPositively = false;
afterEach(() => (hasUsedContainsPositively = false));
/**
 * @typedef {[string, ContainsOptions]} ContainsTuple tuple representing params of the contains
 *  function, where the first element is the selector, and the second element is the options param.
 * @typedef {Object} ContainsOptions
 * @property {ContainsTuple} [after] if provided, the found element(s) must be after the element
 *  matched by this param.
 * @property {ContainsTuple} [before] if provided, the found element(s) must be before the element
 *  matched by this param.
 * @property {Object} [click] if provided, clicks on the first found element
 * @property {ContainsTuple|ContainsTuple[]} [contains] if provided, the found element(s) must
 *  contain the provided sub-elements.
 * @property {number} [count=1] numbers of elements to be found to declare the contains check
 *  as successful. Elements are counted after applying all other filters.
 * @property {Object[]} [dragenterFiles] if provided, dragenters the given files on the found element
 * @property {Object[]} [dragoverFiles] if provided, dragovers the given files on the found element
 * @property {Object[]} [dropFiles] if provided, drops the given files on the found element
 * @property {Object[]} [inputFiles] if provided, inputs the given files on the found element
 * @property {{content:string, replace:boolean}} [insertText] if provided, adds to (or replace) the
 *  value of the first found element by the given content.
 * @property {ContainsTuple} [parent] if provided, the found element(s) must have as
 *  parent the node matching the parent parameter.
 * @property {Object[]} [pasteFiles] if provided, pastes the given files on the found element
 * @property {number|"bottom"} [scroll] if provided, the scrollTop of the found element(s)
 *  must match.
 *  Note: when using one of the scrollTop options, it is advised to ensure the height is not going
 *  to change soon, by checking with a preceding contains that all the expected elements are in DOM.
 * @property {boolean} [setFocus] if provided, focuses the first found element.
 * @property {boolean} [shadowRoot] if provided, targets the shadowRoot of the found elements.
 * @property {number|"bottom"} [setScroll] if provided, sets the scrollTop on the first found
 *  element.
 * @property {HTMLElement|OdooEnv} [target=getFixture()]
 * @property {string[]} [triggerEvents] if provided, triggers the given events on the found element
 * @property {string} [text] if provided, the textContent of the found element(s) or one of their
 *  descendants must match. Use `textContent` option for a match on the found element(s) only.
 * @property {string} [textContent] if provided, the textContent of the found element(s) must match.
 *  Prefer `text` option for a match on the found element(s) or any of their descendants, usually
 *  allowing for a simpler and less specific selector.
 * @property {string} [value] if provided, the input value of the found element(s) must match.
 *  Note: value changes are not observed directly, another mutation must happen to catch them.
 * @property {boolean} [visible] if provided, the found element(s) must be (in)visible
 */
class Contains {
    /**
     * @param {string} selector
     * @param {ContainsOptions} [options={}]
     */
    constructor(selector, options = {}) {
        this.selector = selector;
        this.options = options;
        this.options.count ??= 1;
        let targetParam;
        if (this.options.target?.testEnv) {
            // when OdooEnv, special key `target`. See @start
            targetParam = this.options.target?.target;
        }
        if (!targetParam) {
            targetParam = this.options.target;
        }
        this.options.target = targetParam || getFixture();
        let selectorMessage = `${this.options.count} of "${this.selector}"`;
        if (this.options.visible !== undefined) {
            selectorMessage = `${selectorMessage} ${
                this.options.visible ? "visible" : "invisible"
            }`;
        }
        if (targetParam) {
            selectorMessage = `${selectorMessage} inside a specific target`;
        }
        if (this.options.parent) {
            selectorMessage = `${selectorMessage} inside a specific parent`;
        }
        if (this.options.contains) {
            selectorMessage = `${selectorMessage} with a specified sub-contains`;
        }
        if (this.options.text !== undefined) {
            selectorMessage = `${selectorMessage} with text "${this.options.text}"`;
        }
        if (this.options.textContent !== undefined) {
            selectorMessage = `${selectorMessage} with textContent "${this.options.textContent}"`;
        }
        if (this.options.value !== undefined) {
            selectorMessage = `${selectorMessage} with value "${this.options.value}"`;
        }
        if (this.options.scroll !== undefined) {
            selectorMessage = `${selectorMessage} with scroll "${this.options.scroll}"`;
        }
        if (this.options.after !== undefined) {
            selectorMessage = `${selectorMessage} after a specified element`;
        }
        if (this.options.before !== undefined) {
            selectorMessage = `${selectorMessage} before a specified element`;
        }
        this.selectorMessage = selectorMessage;
        if (this.options.contains && !Array.isArray(this.options.contains[0])) {
            this.options.contains = [this.options.contains];
        }
        if (this.options.count) {
            hasUsedContainsPositively = true;
        } else if (!hasUsedContainsPositively) {
            throw new Error(
                `Starting a test with "contains" of count 0 for selector "${this.selector}" is useless because it might immediately resolve. Start the test by checking that an expected element actually exists.`
            );
        }
        /** @type {string} */
        this.successMessage = undefined;
        /** @type {function} */
        this.executeError = undefined;
    }

    /**
     * Starts this contains check, either immediately resolving if there is a
     * match, or registering appropriate listeners and waiting until there is a
     * match or a timeout (resolving or rejecting respectively).
     *
     * Success or failure messages will be logged with HOOT as well.
     *
     * @returns {Promise}
     */
    run() {
        this.done = false;
        this.def = new Deferred();
        this.scrollListeners = new Set();
        this.onScroll = () => this.runOnce("after scroll");
        if (!this.runOnce("immediately")) {
            this.timer = setTimeout(
                () => this.runOnce("Timeout of 3 seconds", { crashOnFail: true }),
                3000
            );
            this.observer = new MutationObserver((mutations) => {
                try {
                    this.runOnce("after mutations");
                } catch (e) {
                    this.def.reject(e); // prevents infinite loop in case of programming error
                }
            });
            this.observer.observe(document.body, {
                attributes: true,
                childList: true,
                subtree: true,
            });
            after(() => {
                if (!this.done) {
                    this.runOnce("Test ended", { crashOnFail: true });
                }
            });
        }
        return this.def;
    }

    /**
     * Runs this contains check once, immediately returning the result (or
     * undefined), and possibly resolving or rejecting the main promise
     * (and printing HOOT log) depending on options.
     * If undefined is returned it means the check was not successful.
     *
     * @param {string} whenMessage
     * @param {Object} [options={}]
     * @param {boolean} [options.crashOnFail=false]
     * @param {boolean} [options.executeOnSuccess=true]
     * @returns {HTMLElement[]|undefined}
     */
    runOnce(whenMessage, { crashOnFail = false, executeOnSuccess = true } = {}) {
        const res = this.select();
        if ((res?.length ?? 0) === this.options.count || crashOnFail) {
            // clean before doing anything else to avoid infinite loop due to side effects
            this.observer?.disconnect();
            clearTimeout(this.timer);
            for (const el of this.scrollListeners ?? []) {
                el.removeEventListener("scroll", this.onScroll);
            }
            this.done = true;
        }
        if ((res?.length ?? 0) === this.options.count) {
            this.successMessage = `Found ${this.selectorMessage} (${whenMessage})`;
            if (executeOnSuccess) {
                this.executeAction(res[0]);
            }
            return res;
        } else {
            this.executeError = () => {
                let message = `Failed to find ${this.selectorMessage} (${whenMessage}).`;
                message = res
                    ? `${message} Found ${res.length} instead.`
                    : `${message} Parent not found.`;
                if (this.parentContains) {
                    if (this.parentContains.successMessage) {
                        log(true, this.parentContains.successMessage);
                    } else {
                        this.parentContains.executeError();
                    }
                }
                log(false, message);
                this.def?.reject(new Error(message));
                for (const childContains of this.childrenContains || []) {
                    if (childContains.successMessage) {
                        log(true, childContains.successMessage);
                    } else {
                        childContains.executeError();
                    }
                }
            };
            if (crashOnFail) {
                this.executeError();
            }
        }
    }

    /**
     * Executes the action(s) given to this constructor on the found element,
     * prints the success messages, and resolves the main deferred.

     * @param {HTMLElement} el
     */
    executeAction(el) {
        let message = this.successMessage;
        if (this.options.click) {
            message = `${message} and clicked it`;
            _click(el, undefined, {
                mouseEventInit: this.options.click,
                skipDisabledCheck: true,
                skipVisibilityCheck: true,
            });
        }
        if (this.options.dragenterFiles) {
            message = `${message} and dragentered ${this.options.dragenterFiles.length} file(s)`;
            const ev = new Event("dragenter", { bubbles: true });
            Object.defineProperty(ev, "dataTransfer", {
                value: createFakeDataTransfer(this.options.dragenterFiles),
            });
            el.dispatchEvent(ev);
        }
        if (this.options.dragoverFiles) {
            message = `${message} and dragovered ${this.options.dragoverFiles.length} file(s)`;
            const ev = new Event("dragover", { bubbles: true });
            Object.defineProperty(ev, "dataTransfer", {
                value: createFakeDataTransfer(this.options.dragoverFiles),
            });
            el.dispatchEvent(ev);
        }
        if (this.options.dropFiles) {
            message = `${message} and dropped ${this.options.dropFiles.length} file(s)`;
            const ev = new Event("drop", { bubbles: true });
            Object.defineProperty(ev, "dataTransfer", {
                value: createFakeDataTransfer(this.options.dropFiles),
            });
            el.dispatchEvent(ev);
        }
        if (this.options.inputFiles) {
            message = `${message} and inputted ${this.options.inputFiles.length} file(s)`;
            // could not use _createFakeDataTransfer as el.files assignation will only
            // work with a real FileList object.
            const dataTransfer = new window.DataTransfer();
            for (const file of this.options.inputFiles) {
                dataTransfer.items.add(file);
            }
            el.files = dataTransfer.files;
            /**
             * Changing files programatically is not supposed to trigger the event but
             * it does in Chrome versions before 73 (which is on runbot), so in that
             * case there is no need to make a manual dispatch, because it would lead to
             * the files being added twice.
             */
            const versionRaw = navigator.userAgent.match(/Chrom(e|ium)\/([0-9]+)\./);
            const chromeVersion = versionRaw ? parseInt(versionRaw[2], 10) : false;
            if (!chromeVersion || chromeVersion >= 73) {
                el.dispatchEvent(new Event("change"));
            }
        }
        if (this.options.insertText !== undefined) {
            message = `${message} and inserted text "${this.options.insertText.content}" (replace: ${this.options.insertText.replace})`;
            el.focus();
            if (this.options.insertText.replace) {
                el.value = "";
                el.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Backspace" }));
                el.dispatchEvent(new window.KeyboardEvent("keyup", { key: "Backspace" }));
                el.dispatchEvent(new window.InputEvent("input"));
            }
            for (const char of this.options.insertText.content) {
                el.value += char;
                el.dispatchEvent(new window.KeyboardEvent("keydown", { key: char }));
                el.dispatchEvent(new window.KeyboardEvent("keyup", { key: char }));
                el.dispatchEvent(new window.InputEvent("input"));
            }
            el.dispatchEvent(new window.InputEvent("change"));
        }
        if (this.options.pasteFiles) {
            message = `${message} and pasted ${this.options.pasteFiles.length} file(s)`;
            const ev = new Event("paste", { bubbles: true });
            Object.defineProperty(ev, "clipboardData", {
                value: createFakeDataTransfer(this.options.pasteFiles),
            });
            el.dispatchEvent(ev);
        }
        if (this.options.setFocus) {
            message = `${message} and focused it`;
            el.focus();
        }
        if (this.options.setScroll !== undefined) {
            message = `${message} and set scroll to "${this.options.setScroll}"`;
            el.scrollTop =
                this.options.setScroll === "bottom" ? el.scrollHeight : this.options.setScroll;
        }
        if (this.options.triggerEvents) {
            message = `${message} and triggered "${this.options.triggerEvents.join(", ")}" events`;
            _triggerEvents(el, null, this.options.triggerEvents, {
                skipVisibilityCheck: true,
            });
        }
        if (this.parentContains) {
            log(true, this.parentContains.successMessage);
        }
        log(true, message);
        for (const childContains of this.childrenContains) {
            log(true, childContains.successMessage);
        }
        this.def?.resolve();
    }

    /**
     * Returns the found element(s) according to this constructor setup.
     * If undefined is returned it means the parent cannot be found
     *
     * @returns {HTMLElement[]|undefined}
     */
    select() {
        const target = this.selectParent();
        if (!target) {
            return;
        }
        let elems;
        if (target === getFixture() && queryFirst(this.selector) === target) {
            elems = [target];
        } else {
            elems = queryAll(this.selector, { root: target });
        }
        const baseRes = elems
            .map((el) => (this.options.shadowRoot ? el.shadowRoot : el))
            .filter((el) => el);
        /** @type {Contains[]} */
        this.childrenContains = [];
        const res = baseRes.filter((el, currentIndex) => {
            let condition =
                (this.options.textContent === undefined ||
                    el.textContent.trim() === this.options.textContent) &&
                (this.options.value === undefined || el.value === this.options.value) &&
                (this.options.scroll === undefined ||
                    (this.options.scroll === "bottom"
                        ? Math.abs(el.scrollHeight - el.clientHeight - el.scrollTop) <= 1
                        : Math.abs(el.scrollTop - this.options.scroll) <= 1));
            if (condition && this.options.text !== undefined) {
                if (
                    el.textContent.trim() !== this.options.text &&
                    [...el.querySelectorAll("*")].every(
                        (el) => el.textContent.trim() !== this.options.text
                    )
                ) {
                    condition = false;
                }
            }
            if (condition && this.options.contains) {
                for (const param of this.options.contains) {
                    const childContains = new Contains(param[0], { ...param[1], target: el });
                    if (
                        !childContains.runOnce(`as child of el ${currentIndex + 1})`, {
                            executeOnSuccess: false,
                        })
                    ) {
                        condition = false;
                    }
                    this.childrenContains.push(childContains);
                }
            }
            if (condition && this.options.visible !== undefined) {
                if (isVisible(el) !== this.options.visible) {
                    condition = false;
                }
            }
            if (condition && this.options.after) {
                const afterContains = new Contains(this.options.after[0], {
                    ...this.options.after[1],
                    target,
                });
                const afterEl = afterContains.runOnce(`as "after"`, {
                    executeOnSuccess: false,
                })?.[0];
                if (
                    !afterEl ||
                    !(el.compareDocumentPosition(afterEl) & Node.DOCUMENT_POSITION_PRECEDING)
                ) {
                    condition = false;
                }
                this.childrenContains.push(afterContains);
            }
            if (condition && this.options.before) {
                const beforeContains = new Contains(this.options.before[0], {
                    ...this.options.before[1],
                    target,
                });
                const beforeEl = beforeContains.runOnce(`as "before"`, {
                    executeOnSuccess: false,
                })?.[0];
                if (
                    !beforeEl ||
                    !(el.compareDocumentPosition(beforeEl) & Node.DOCUMENT_POSITION_FOLLOWING)
                ) {
                    condition = false;
                }
                this.childrenContains.push(beforeContains);
            }
            return condition;
        });
        if (
            this.options.scroll !== undefined &&
            this.scrollListeners &&
            baseRes.length === this.options.count &&
            res.length !== this.options.count
        ) {
            for (const el of baseRes) {
                if (!this.scrollListeners.has(el)) {
                    this.scrollListeners.add(el);
                    el.addEventListener("scroll", this.onScroll);
                }
            }
        }
        return res;
    }

    /**
     * Returns the found element that should act as the target (parent) for the
     * main selector.
     * If undefined is returned it means the parent cannot be found.
     *
     * @returns {HTMLElement|undefined}
     */
    selectParent() {
        if (this.options.parent) {
            this.parentContains = new Contains(this.options.parent[0], {
                ...this.options.parent[1],
                target: this.options.target,
            });
            return this.parentContains.runOnce(`as parent`, { executeOnSuccess: false })?.[0];
        }
        return this.options.target;
    }
}

/**
 * Waits until `count` elements matching the given `selector` are present in
 * `options.target`.
 *
 * @param {string} selector
 * @param {ContainsOptions} [options]
 * @returns {Promise}
 */
export async function contains(selector, options) {
    await new Contains(selector, options).run();
}

const stepState = {
    expectedSteps: null,
    /** @type {Promise} */
    deferred: null,
    timeout: null,
    currentSteps: [],

    clear() {
        clearTimeout(this.timeout);
        this.timeout = null;
        this.deferred = null;
        this.currentSteps = [];
        this.expectedSteps = null;
    },

    check({ crashOnFail = false } = {}) {
        const success =
            this.expectedSteps.length === this.currentSteps.length &&
            this.expectedSteps.every((s, i) => s === this.currentSteps[i]);
        if (!success && !crashOnFail) {
            return;
        }
        expect.verifySteps(this.expectedSteps);
        if (success) {
            this.deferred.resolve();
        } else {
            this.deferred.reject(new Error("Steps do not match."));
        }
        this.clear();
    },
};

afterEach(() => {
    if (stepState.expectedSteps) {
        stepState.check({ crashOnFail: true });
    } else {
        stepState.clear();
    }
});

/**
 * Indicate the completion of a test step. This step must then be verified by
 * calling `assertSteps`.
 *
 * @param {string} step
 */
export function step(step) {
    stepState.currentSteps.push(step);
    expect.step(step);
    if (stepState.expectedSteps) {
        stepState.check();
    }
}

/**
 * Wait for the given steps to be executed or for the timeout to be reached.
 *
 * @param {string[]} steps
 */
export function assertSteps(steps) {
    if (stepState.expectedSteps) {
        stepState.check({ crashOnFail: true });
    }
    stepState.expectedSteps = steps;
    stepState.deferred = new Deferred();
    stepState.timeout = setTimeout(() => stepState.check({ crashOnFail: true }), 2000);
    stepState.check();
    return stepState.deferred;
}
