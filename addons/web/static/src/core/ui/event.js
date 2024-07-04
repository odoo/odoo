const delegateEvent = function (ev) {
    let target = ev.target;
    const pseudoSelectorRegex = /:[\w-]+(\([^)]*\))?/g;

    if (typeof this.selector === "string") {
        // Remove pseudo selectors from the selector
        const cleanSelector = pseudoSelectorRegex.test(this.selector)
            ? this.selector.replace(pseudoSelectorRegex, "")
            : this.selector;

        // Attempt to find the matching target
        while (target.parentElement && target !== this.element && !target?.matches(cleanSelector)) {
            target = target.parentElement;
        }
        if (target?.matches(cleanSelector)) {
            // Create a new event and set its currentTarget
            Object.defineProperty(ev, "currentTarget", {
                get: () => target,
                configurable: true,
            });
            this.handler.call(target, ev);
        }
    } else {
        // Selector is not provided, directly use this.element as the context
        this.handler = this.selector;
        this.handler.call(this.element, ev);
    }
};

const events = new WeakMap();

/**
 * Event delegation
 * Example:
 * - Element.on('click', function()) => Bind event to the element
 * - Element.on('click', 'selector', function()) => Bind event to all elements matches selector
 *
 * - EventName string should be "eventType.Namespace" or "eventType", where Namespace should be
 * unique for the different groups.
 *
 * @private
 * @param {string} eventName Name of the events E.g. 'click', 'click.MyClick'
 * @param {String || Element} selector Element/selector to apply event delegation
 * @param {Function} handler Callback to delegate
 * @param {Object} options Extra paramete e.g. capture...
 */
HTMLElement.prototype.on = function (eventName, selector, handler, options = {}) {
    const eventNames = eventName.split(", ");
    // To handle multiple event namespace, e.g. "event.Event1 event.Event2".
    for (eventName of eventNames) {
        const capture = !!options.capture;
        const selectorKey = typeof selector === "string" ? selector.replace(/ /g, "_") : "";
        const eventKey = selectorKey
            ? `${eventName}_${selectorKey}_${capture}`
            : `${eventName}_${capture}`;
        if (!events.has(this)) {
            events.set(this, new Map());
        }
        const eventMap = events.get(this);
        if (!eventMap.has(eventKey)) {
            eventMap.set(eventKey, new Set());
        }
        const boundFn = delegateEvent.bind({ element: this, selector, handler });
        eventMap.get(eventKey).add(boundFn);
        boundFn.handler = handler;
        this.addEventListener(eventKey.split(".")[0], boundFn, options);
    }
};

// Event delegation for Window
// Since Window is not a HTMLElement, we need to extend it to support on/off events.
Window.prototype.on = function (eventName, selector, handler, options = {}) {
    HTMLElement.prototype.on.call(this, eventName, selector, handler, options);
};

// Event delegation for Document
// Since Document is not a HTMLElement, we need to extend it to support on/off events.
Document.prototype.on = function (eventName, selector, handler, options = {}) {
    HTMLElement.prototype.on.call(this, eventName, selector, handler, options);
};

/**
 * Event delegation
 *
 * Example.
 * - Element.off() => remove all events from element
 * - Element.off('click') => remove all click events from element
 * - Element.off('click', 'div') => remove all click events bind to the div
 * - Element.off('click', 'div', function()) => remove given function from eventlistner
 *
 */
HTMLElement.prototype.off = function (eventName = "", selector, handler, options = {}) {
    const eventNames = eventName.split(", ");
    // To handle multiple event namespace, e.g. "event.Event1 event.Event2".
    for (eventName of eventNames) {
        const capture = !!options.capture;
        if (events.has(this)) {
            const eventMap = events.get(this);
            if (selector) {
                const selectorString =
                    typeof selector === "string" ? selector.replace(/ /g, "_") : "";
                const eventKey = `${eventName}_${selectorString}_${capture}`;
                const handlers = eventMap.get(eventKey) || [];
                const filteredHandlers = [...handlers].filter((boundFn) => {
                    if (!handler || handler === boundFn.handler) {
                        this.removeEventListener(eventKey.split(".")[0], boundFn, options);
                        return false; // Remove this handler
                    }
                    return true; // Keep this handler
                });
                eventMap.set(eventKey, filteredHandlers);
                if (!eventMap.get(eventKey).length) {
                    eventMap.delete(eventKey);
                }
            } else {
                eventMap.forEach((handlers, eventKey) => {
                    // Check for eventName is,
                    // 1. evenet_type + namespace e.g. "click.MyClick"
                    // 2. only namespace e.g. ".MyClick"
                    // 3. only event_type e.g. "click"
                    if (
                        eventKey.startsWith(`${eventName}_`) ||
                        eventKey.split(".")[0]?.startsWith(eventName) ||
                        eventKey.split(".")[1]?.startsWith(eventName.split(".")[1])
                    ) {
                        handlers.forEach((boundFn) => {
                            this.removeEventListener(eventKey.split(".")[0], boundFn, options);
                        });
                        eventMap.delete(eventKey);
                    }
                });
            }
            if (eventMap.size === 0) {
                events.delete(this);
            }
        }
    }
};

Window.prototype.off = function (eventName, selector, handler, options = {}) {
    HTMLElement.prototype.off.call(this, eventName, selector, handler, options);
};

Document.prototype.off = function (eventName, selector, handler, options = {}) {
    HTMLElement.prototype.off.call(this, eventName, selector, handler, options);
};
