// eventUtils.js

const events = new WeakMap();

const delegateEvent = function (ev) {
    let target = ev.target;
    const updateObject = () => {
        Object.defineProperty(ev, "currentTarget", {
            get: () => target,
            configurable: true,
        });
    };

    if (typeof this.selector === "string") {
        while (target && target !== this.element) {
            try {
                if (target.matches(this.selector)) {
                    updateObject();
                    this.handler.call(this.element, ev);
                    return;
                }
            } catch {
                /* empty */
            }
            target = target.parentElement;
        }
        if (target.matches(this.selector)) {
            updateObject();
            this.handler.call(target, ev);
        }
    } else {
        this.handler = this.selector;
        this.handler.call(this.element, ev);
    }
};

const EventUtils = {
    on(element, eventName, selector, handler, options = {}) {
        const eventNames = eventName.split(", ");
        for (eventName of eventNames) {
            const capture = !!options.capture;
            const selectorKey = typeof selector === "string" ? selector.replace(/ /g, "_") : "";
            const eventKey = selectorKey
                ? `${eventName}_${selectorKey}_${capture}`
                : `${eventName}_${capture}`;
            if (!events.has(element)) {
                events.set(element, new Map());
            }
            const eventMap = events.get(element);
            if (!eventMap.has(eventKey)) {
                eventMap.set(eventKey, new Set());
            }
            const boundFn = delegateEvent.bind({ element, selector, handler });
            eventMap.get(eventKey).add(boundFn);
            boundFn.handler = handler;
            element.addEventListener(eventName.split(".")[0], boundFn, options);
        }
    },

    off(element, eventName = "", selector, handler, options = {}) {
        const eventNames = eventName.split(", ");
        for (eventName of eventNames) {
            const capture = !!options.capture;
            if (events.has(element)) {
                const eventMap = events.get(element);
                if (selector) {
                    const selectorString =
                        typeof selector === "string" ? selector.replace(/ /g, "_") : "";
                    const eventKey = `${eventName}_${selectorString}_${capture}`;
                    const handlers = eventMap.get(eventKey) || [];
                    const filteredHandlers = [...handlers].filter((boundFn) => {
                        if (!handler || handler === boundFn.handler) {
                            element.removeEventListener(eventName.split(".")[0], boundFn, options);
                            return false;
                        }
                        return true;
                    });
                    eventMap.set(eventKey, filteredHandlers);
                    if (!eventMap.get(eventKey).length) {
                        eventMap.delete(eventKey);
                    }
                } else {
                    eventMap.forEach((handlers, eventKey) => {
                        if (
                            eventKey.startsWith(`${eventName}_`) ||
                            eventKey.split(".")[0]?.startsWith(eventName) ||
                            eventKey.split(".")[1]?.startsWith(eventName.split(".")[1])
                        ) {
                            handlers.forEach((boundFn) => {
                                element.removeEventListener(
                                    eventName.split(".")[0],
                                    boundFn,
                                    options
                                );
                            });
                            eventMap.delete(eventKey);
                        }
                    });
                }
                if (eventMap.size === 0) {
                    events.delete(element);
                }
            }
        }
    },
};

export default EventUtils;
