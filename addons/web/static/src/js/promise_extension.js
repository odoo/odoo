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
    if (typeof onRejected === 'function') {
        this.catch(function (reason) {
            if (reason instanceof Error) {
                // In the case the original promise was rejected because of a
                // common JS error, we let the error propagate by re-triggering
                // it. Note: this error won't be able to be caught with a
                // subsequent catch though since the internal catch return here
                // is not returned.
                throw reason;
            }
            // ... otherwise execute the rejection handler, ignores its result
            // and async components
            onRejected.call(this, reason);
        });
    }
    // In any case, the jQuery's fail method is desired: return the original
    // promise.
    return this;
};
