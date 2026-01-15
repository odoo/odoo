/** @odoo-module alias=@web/../tests/legacy_tests/helpers/test_utils default=false */

    /**
     * Test Utils
     *
     * In this module, we define various utility functions to help simulate a mock
     * environment as close as possible as a real environment.
     */

    import testUtilsDom from "@web/../tests/legacy_tests/helpers/test_utils_dom";
    import testUtilsFields from "@web/../tests/legacy_tests/helpers/test_utils_fields";
    import testUtilsMock from "@web/../tests/legacy_tests/helpers/test_utils_mock";

    function deprecated(fn, type) {
        return function () {
            const msg = `Helper 'testUtils.${fn.name}' is deprecated. ` +
                `Please use 'testUtils.${type}.${fn.name}' instead.`;
            console.warn(msg);
            return fn.apply(this, arguments);
        };
    }

    /**
     * Helper function, make a promise with a public resolve function. Note that
     * this is not standard and should not be used outside of tests...
     *
     * @returns {Promise + resolve and reject function}
     */
    function makeTestPromise() {
        let resolve;
        let reject;
        const promise = new Promise(function (_resolve, _reject) {
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
        const prom = makeTestPromise();
        prom.then(() => assert.step('ok ' + str)).catch(function () { });
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
    export async function nextTick() {
        return testUtilsDom.returnAfterNextAnimationFrame();
    }

    export const mock = {
        intercept: testUtilsMock.intercept,
        patch: testUtilsMock.patch,
        patchDate: testUtilsMock.patchDate,
        unpatch: testUtilsMock.unpatch,
        getView: testUtilsMock.getView,
    };

    export const dom = {
        dragAndDrop: testUtilsDom.dragAndDrop,
        find: testUtilsDom.findItem,
        click: testUtilsDom.click,
        clickFirst: testUtilsDom.clickFirst,
        triggerEvents: testUtilsDom.triggerEvents,
        triggerEvent: testUtilsDom.triggerEvent,
    };

    export const fields = {
        editInput: testUtilsFields.editInput,
        editAndTrigger: testUtilsFields.editAndTrigger,
        triggerKeydown: testUtilsFields.triggerKeydown,
    };

    export default {
        mock,
        dom,
        fields,

        makeTestPromise: makeTestPromise,
        makeTestPromiseWithAssert: makeTestPromiseWithAssert,
        nextMicrotaskTick: nextMicrotaskTick,
        nextTick: nextTick,

        // backward-compatibility
        dragAndDrop: deprecated(testUtilsDom.dragAndDrop, 'dom'),
        getView: deprecated(testUtilsMock.getView, 'mock'),
        intercept: deprecated(testUtilsMock.intercept, 'mock'),
        openDatepicker: deprecated(testUtilsDom.openDatepicker, 'dom'),
        patch: deprecated(testUtilsMock.patch, 'mock'),
        patchDate: deprecated(testUtilsMock.patchDate, 'mock'),
        unpatch: deprecated(testUtilsMock.unpatch, 'mock'),
    };
