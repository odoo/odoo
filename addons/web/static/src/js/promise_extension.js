/**
 * This file adds a 'guardedCatch' function to the Promise API. This function
 * has to be used to not catch real errors (crashes), like 'catch' does. The
 * 'onRejected' handler is only executed if the rejection's reason is not an
 * Error object, otherwise we let the original rejection reason propagate.
 *
 * Note: we also want the method to behave like 'fail' of jQuery:
 * prom.guardedCatch(1).then(2) should only call (1) if prom is rejected as
 * .fail() returned the original promise.
 */
Promise.prototype.guardedCatch = function (onRejected) {
    const self = this;
    return this.catch(function (reason) {
        if (typeof onRejected !== 'function' || reason instanceof Error) {
            // In the case the method was not given a proper rejection handler
            // or that the original promise was rejected because of a common
            // JS error, we let the rejection propagate by re-triggering it...
            return Promise.reject(reason);
        }
        // ... otherwise the jQuery 'fail' method's behavior is desired: execute
        // the rejection handler, ignores its result and async components and
        // propagate the original promise result (ideally should return the
        // original promise itself, but not possible using native promises) but
        // keep the fact that it has been handled (do not return a new
        // *unhandled* rejected promise).
        onRejected.call(this, reason);
        return self;
    });
};
