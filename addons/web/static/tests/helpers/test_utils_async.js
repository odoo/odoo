odoo.define('web.test_utils_async', function (require) {
"use strict";

const testUtilsDom = require('web.test_utils_dom');


/**
 * Helper function, make a promise with a public resolve function. Note that
 * this is not standard and should not be used outside of tests...
 *
 * @returns {Promise + resolve and reject function}
 */
function makeTestPromise() {
    var resolve;
    var reject;
    var promise = new Promise(function (_resolve, _reject) {
        resolve = _resolve;
        reject = _reject;
    });
    promise.resolve = function () {
        resolve.apply(null, arguments);
        return promise;
    };
    promise.reject = function () {
        reject.apply(null, arguments);
        return promise;
    };
    return promise;
}

/**
 * Make a promise with public resolve and reject functions (see
 * @makeTestPromise). Perform an assert.step when the promise is
 * resolved/rejected.
 *
 * @param {Object} assert instance object with the assertion methods
 * @param {function} assert.step
 * @param {string} str message to pass to assert.step
 * @returns {Promise + resolve and reject function}
 */
function makeTestPromiseWithAssert(assert, str) {
    var prom = makeTestPromise();
    prom.then(() => assert.step('ok ' + str)).catch(function () {});
    prom.catch(() => assert.step('ko ' + str));
    return prom;
}

/**
 * Create a new promise that can be waited by the caller in order to execute
 * code after the next microtask tick and before the next jobqueue tick.
 *
 * @return {Promise} an already fulfilled promise
 */
async function nextMicrotaskTick() {
    return Promise.resolve();
}

/**
 * Returns a promise that will be resolved after the tick after the
 * nextAnimationFrame
 *
 * This is usefull to guarantee that OWL has had the time to render
 *
 * @returns {Promise}
 */
async function nextTick() {
    return testUtilsDom.returnAfterNextAnimationFrame();
}

// Loading static files cannot be properly simulated when their real content is
// really needed. This is the case for static XML files so we load them here,
// before starting the qunit test suite.
// (session.js is in charge of loading the static xml bundle and we also have
// to load xml files that are normally lazy loaded by specific widgets).
return {
    makeTestPromise: makeTestPromise,
    makeTestPromiseWithAssert: makeTestPromiseWithAssert,
    nextMicrotaskTick: nextMicrotaskTick,
    nextTick: nextTick,
};

});
