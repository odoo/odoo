/**
 * Instance of this class is useful in a context of a proxy trap handler.
 * A trap handler's main purpose is to introduce a new behavior which is prone to
 * being recursive. In this case, to avoid infinite recursion, we should be able to track the
 * stack of calls and allow the handler to call the default behavior via the Reflect API.
 *
 * The idea is that when a block of code is called via the `call` method, we increment a counter.
 * If the counter is greater than 0, then we know that we are in a recursive call. We can then
 * use the `isDisabled` method to check if we should call the default behavior or not.
 */
export class TrapDisabler {
    constructor() {
        this.disabled = 0;
    }
    isDisabled() {
        return this.disabled > 0;
    }
    call(fn, ...args) {
        try {
            this.disabled += 1;
            return fn(...args);
        } finally {
            this.disabled -= 1;
        }
    }
}

const disablerCaches = new WeakMap();

export function getDisabler(target, prop) {
    if (!disablerCaches.has(target)) {
        disablerCaches.set(target, new Map());
    }
    const disablerCache = disablerCaches.get(target);
    if (!disablerCache.has(prop)) {
        disablerCache.set(prop, new TrapDisabler());
    }
    return disablerCache.get(prop);
}
