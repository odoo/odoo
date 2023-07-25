/** @odoo-module alias=web.test_utils **/

    /**
     * Test Utils
     *
     * In this module, we define various utility functions to help simulate a mock
     * environment as close as possible as a real environment.
     */

    import testUtilsDom from "web.test_utils_dom";
    import testUtilsFields from "web.test_utils_fields";
    import testUtilsFile from "web.test_utils_file";
    import testUtilsMock from "web.test_utils_mock";
    import Widget from "web.Widget";

    function deprecated(fn, type) {
        return function () {
            const msg = `Helper 'testUtils.${fn.name}' is deprecated. ` +
                `Please use 'testUtils.${type}.${fn.name}' instead.`;
            console.warn(msg);
            return fn.apply(this, arguments);
        };
    }

    /**
     * Create a widget parent from given parameters.
     *
     * @param {Object} params This object will be given to addMockEnvironment, so
     *   any parameters from that method applies
     * @returns {Promise<Widget>}
     */
    async function createParent(params) {
        const widget = new Widget();
        await testUtilsMock.addMockEnvironment(widget, params);
        return widget;
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
    async function nextTick() {
        return testUtilsDom.returnAfterNextAnimationFrame();
    }

    export default {
        mock: {
            addMockEnvironment: testUtilsMock.addMockEnvironment,
            addMockEnvironmentOwl: testUtilsMock.addMockEnvironmentOwl,
            intercept: testUtilsMock.intercept,
            patch: testUtilsMock.patch,
            patchDate: testUtilsMock.patchDate,
            unpatch: testUtilsMock.unpatch,
            getView: testUtilsMock.getView,
        },
        dom: {
            dragAndDrop: testUtilsDom.dragAndDrop,
            find: testUtilsDom.findItem,
            click: testUtilsDom.click,
            clickFirst: testUtilsDom.clickFirst,
            triggerEvents: testUtilsDom.triggerEvents,
            triggerEvent: testUtilsDom.triggerEvent,
        },
        fields: {
            editInput: testUtilsFields.editInput,
            editAndTrigger: testUtilsFields.editAndTrigger,
            triggerKeydown: testUtilsFields.triggerKeydown,
        },
        file: {
            createFile: testUtilsFile.createFile,
            dragoverFile: testUtilsFile.dragoverFile,
            dropFile: testUtilsFile.dropFile,
            dropFiles: testUtilsFile.dropFiles,
            inputFiles: testUtilsFile.inputFiles,
        },

        createParent,
        makeTestPromise: makeTestPromise,
        makeTestPromiseWithAssert: makeTestPromiseWithAssert,
        nextMicrotaskTick: nextMicrotaskTick,
        nextTick: nextTick,

        // backward-compatibility
        addMockEnvironment: deprecated(testUtilsMock.addMockEnvironment, 'mock'),
        dragAndDrop: deprecated(testUtilsDom.dragAndDrop, 'dom'),
        getView: deprecated(testUtilsMock.getView, 'mock'),
        intercept: deprecated(testUtilsMock.intercept, 'mock'),
        openDatepicker: deprecated(testUtilsDom.openDatepicker, 'dom'),
        patch: deprecated(testUtilsMock.patch, 'mock'),
        patchDate: deprecated(testUtilsMock.patchDate, 'mock'),
        unpatch: deprecated(testUtilsMock.unpatch, 'mock'),
    };
