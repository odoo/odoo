/**
 * This file adds a 'guardedCatch' function to the Promise API. This function
 * has to be used when we don't want to swallow real errors (crashes), like
 * 'catch' does (i.e. basically all the time in Odoo). We only execute the
 * 'onRejected' handler if the rejection's reason is not an Error, and we always
 * return a rejected Promise to let the rejection bubble up (and trigger the
 * 'unhandledrejection' event).
 */

(function () {
    var _catch = Promise.prototype.catch;
    Promise.prototype.guardedCatch = function (onRejected) {
        return _catch.call(this, function (reason) {
            if (!reason || !(reason instanceof Error)) {
                if (onRejected) {
                    onRejected.call(this, reason);
                }
            }
            return Promise.reject(reason);
        });
    };
})();
