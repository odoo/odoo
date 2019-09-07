// based on https://github.com/ustccjw/unhandled-rejection-polyfill
(function () {
"use strict";

var self = window;
var OriginalPromise = self.Promise;

function dispatchUnhandledRejectionEvent(promise, reason) {
    var event = document.createEvent('Event');
    Object.defineProperties(event, {
        promise: {
            value: promise,
            writable: false,
        },
        reason: {
            value: reason,
            writable: false,
        },
    });
    event.initEvent('unhandledrejection', false, true);
    window.dispatchEvent(event);
}

function MyPromise(resolver) {
    if (!(this instanceof MyPromise)) {
        throw new TypeError('Cannot call a class as a function');
    }
    var promise = new OriginalPromise(function (resolve, reject) {
        var customReject = function (reason) {
            // macro-task (setTimeout) will execute after micro-task (promise)
            setTimeout(function () {
                if (promise.handled !== true) {
                    dispatchUnhandledRejectionEvent(promise, reason);
                }
            }, 0);
            return reject(reason);
        };
        try {
            return resolver(resolve, customReject);
        } catch (err) {
            return customReject(err);
        }
    });
    promise.__proto__ = MyPromise.prototype;
    return promise;
}

MyPromise.__proto__ = OriginalPromise;
MyPromise.prototype.__proto__ = OriginalPromise.prototype;


MyPromise.prototype.then = function (resolve, reject) {
    var self = this;
    return OriginalPromise.prototype.then.call(this, resolve, reject && (function (reason) {
        self.handled = true;
        return reject(reason);
    }));
};

MyPromise.prototype.catch = function (reject) {
    var self = this;
    return OriginalPromise.prototype.catch.call(this, reject && (function (reason) {
        self.handled = true;
        return reject(reason);
    }));
};

MyPromise.polyfill = function () {
    if (typeof PromiseRejectionEvent === 'undefined') {
        window.Promise = MyPromise;
    }
};
MyPromise.polyfill();

})();
