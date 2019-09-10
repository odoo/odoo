odoo.define('web.bus_tests', function (require) {
"use strict";

const BusService = require('bus.BusService');

const AbstractStorageService = require('web.AbstractStorageService');
const RamStorage = require('web.RamStorage');
const testUtils = require('web.test_utils');
const Widget = require('web.Widget');

// TODO: make smaller and sooner verifySteps();
QUnit.module('Bus', {
    beforeEach() {
        /**
         * Special bus service with mocked timeouts
         */
        this.MockedBusService = BusService.extend({
            /**
             * @override
             */
            init() {
                this.testTimeouts = [];
                this.nextTestTimeoutId = 1;
                this._super(...arguments);
            },
            testProceedTimeouts() {
                const testTimeouts = [...this.testTimeouts];
                while (testTimeouts.length > 0) {
                    const testTimeout = testTimeouts.shift();
                    this.testTimeouts.shift();
                    testTimeout.func();
                }
            },
            /**
             * @override
             * @private
             * @param {integer} timeoutId
             */
            _clearTimeout(timeoutId) {
                this.testTimeouts = this.testTimeouts.filter(testTimeout =>
                    testTimeout.id !== timeoutId);
            },
            /**
             * @override
             * @private
             * @param {Function} func
             * @param {integer} duration
             * @return {integer}
             */
            _setTimeout(func, duration) {
                const testTimeoutId = this.nextTestTimeoutId;
                this.testTimeouts.push({
                    duration,
                    func,
                    id: testTimeoutId,
                    timestamp: Date.now(),
                });
                this.nextTestTimeoutId++;
                return testTimeoutId;
            },
        });
        /**
         * Local storage service that uses local storage somewhat like Firefox
         * implementation of local storage: each tab have their own "local
         * storage", which are synchronized throught StorageEvent.
         * To simulate that, each tab have their own local storage, and any
         * setItem/removeItem update other local storages.
         */
        const globalLocalStorage = new RamStorage();
        let nextMockedLocalStorageServiceId = 1;
        const mockedLocalStorageServices = [];
        /**
         * @param {Object} param0
         * @param {integer} param0.from LocalStorageService testId
         * @param {string} param0.key
         * @param {string} param0.type 'removeItem' or 'setItem'
         * @param {any} param0.value
         */
        function notifyLocalStorageServices({ from, key, type, value }) {
            globalLocalStorage[type](key, value);
            for (const mockedLocalStorageService of mockedLocalStorageServices) {
                if (mockedLocalStorageService.__testLocalStorageServiceId === from) {
                    continue;
                }
                let prom = Promise.resolve();
                if (mockedLocalStorageServices.isTestSlowPromPending) {
                    prom = mockedLocalStorageService.testSlowProm;
                }
                prom.then(() => {
                    mockedLocalStorageService.testMakeSlowProm();
                    mockedLocalStorageService.testSlowProm.then(() => {
                        mockedLocalStorageService.storage[type](key, value);
                        mockedLocalStorageService.testSlowProm = testUtils.makeTestPromise();
                    });
                });
            }
        }
        const MockedLocalStorageService = AbstractStorageService.extend({
            /**
             * @override
             */
            init() {
                this.__testLocalStorageServiceId = nextMockedLocalStorageServiceId;
                nextMockedLocalStorageServiceId++;
                mockedLocalStorageServices.push(this);
                this.isTestSlowPromPending = false;
                this.testSlowProm = null;
                this._super(...arguments);
            },
            /**
             * @override
             * @param {string} key
             */
            removeItem(key) {
                this._super(...arguments);
                notifyLocalStorageServices({
                    from: this.__testLocalStorageServiceId,
                    key,
                    type: 'removeItem',
                });
            },
            /**
             * @override
             * @param {string} key
             * @param {any} value
             */
            setItem(key, value) {
                this._super(...arguments);
                notifyLocalStorageServices({
                    from: this.__testLocalStorageServiceId,
                    key,
                    value: JSON.stringify(value),
                    type: 'setItem',
                });
            },
            testMakeSlowProm() {
                this.isTestSlowPromPending = true;
                this.testSlowProm = new Promise(resolve => {
                    if (typeof this.TEST_SLOW_DURATION === 'number') {
                        setTimeout(() => {
                            this.isTestSlowPromPending = false;
                            resolve();
                        }, this.TEST_SLOW_DURATION);
                    } else {
                        this.isTestSlowPromPending = false;
                        resolve();
                    }
                });
            },
        });
        /**
         * @param {Object} [param0={}]
         * @param {integer|null} [param0.testSlowDuration=null] if set, local
         *   storage service will take this amount of milli-seconds to update
         *   its current tab local storage. This is useful to simulate throttled
         *   background tabs with Firefox implementation of per-tab cached local
         *   storages. A value of `null` will make it react on next micro task
         *   tick.
         */
        this.makeMockedLocalStorageService = ({ testSlowDuration=null }={}) =>
            MockedLocalStorageService.extend({
                TEST_SLOW_DURATION: testSlowDuration,
                init() {
                    this.storage = new RamStorage();
                    for (let index = 0; index < globalLocalStorage.length; index++) {
                        const key = globalLocalStorage.key(index);
                        this.storage[key] = globalLocalStorage.storage[key];
                    }
                    this._super(...arguments);
                },
            });
    },
}, function () {

QUnit.test('notifications received from the longpolling channel', async function (assert) {
    assert.expect(6);

    let pollPromise = testUtils.makeTestPromise();
    const parent = new Widget();
    testUtils.mock.addMockEnvironment(parent, {
        data: {},
        mockRPC(route, args) {
            if (route === '/longpolling/poll') {
                assert.step(`${route} - ${args.channels.join(',')}`);
                pollPromise = testUtils.makeTestPromise();
                pollPromise.abort = (function () {
                    this.reject({
                        message: "XmlHttpRequestError abort",
                    }, $.Event());
                }).bind(pollPromise);
                return pollPromise;
            }
            return this._super(...arguments);
        },
        services: {
            bus_service: this.MockedBusService,
            local_storage: this.makeMockedLocalStorageService(),
        },
    });
    const widget = new Widget(parent);
    widget.call('bus_service', 'onNotification', this, notifications =>
        assert.step(`notification - ${notifications.toString()}`));
    widget.call('bus_service', 'addChannel', 'lambda');
    await widget.appendTo($('#qunit-fixture'));
    widget.call('bus_service', 'testProceedTimeouts');
    pollPromise.resolve([{
        id: 1,
        channel: 'lambda',
        message: 'beta',
    }]);
    await testUtils.nextTick();
    pollPromise.resolve([{
        id: 2,
        channel: 'lambda',
        message: 'epsilon',
    }]);
    await testUtils.nextTick();
    assert.verifySteps([
        '/longpolling/poll - lambda',
        'notification - lambda,beta',
        '/longpolling/poll - lambda',
        'notification - lambda,epsilon',
        '/longpolling/poll - lambda',
    ]);

    parent.destroy();
});

QUnit.test('provide notification ID of 0 by default', async function (assert) {
    // This test is important in order to ensure that we provide the correct
    // sentinel value 0 when we are not aware of the last notification ID
    // that we have received. We cannot provide an ID of -1, otherwise it
    // may likely be handled incorrectly (before this test was written,
    // it was providing -1 to the server, which in return sent every stored
    // notifications related to this user).
    assert.expect(3);

    let pollPromise = testUtils.makeTestPromise();
    const parent = new Widget();
    testUtils.mock.addMockEnvironment(parent, {
        data: {},
        mockRPC: function (route, args) {
            if (route === '/longpolling/poll') {
                assert.step(route);
                assert.strictEqual(args.last, 0,
                    "provided last notification ID should be 0");
                pollPromise = testUtils.makeTestPromise();
                pollPromise.abort = (function () {
                    this.reject({
                        message: "XmlHttpRequestError abort",
                    }, $.Event());
                }).bind(pollPromise);
                return pollPromise;
            }
            return this._super(...arguments);
        },
        services: {
            bus_service: this.MockedBusService,
            local_storage: this.makeMockedLocalStorageService(),
        },
    });
    const widget = new Widget(parent);
    await widget.appendTo($('#qunit-fixture'));
    // trigger longpolling poll RPC
    widget.call('bus_service', 'addChannel', 'lambda');
    widget.call('bus_service', 'testProceedTimeouts');
    await testUtils.nextTick();
    assert.verifySteps(['/longpolling/poll']);

    parent.destroy();
});

QUnit.test('cross tab bus share message from a channel', async function (assert) {
    assert.expect(5);

    // slave
    const parentSlave = new Widget();
    testUtils.mock.addMockEnvironment(parentSlave, {
        data: {},
        services: {
            bus_service: this.MockedBusService,
            local_storage: this.makeMockedLocalStorageService(),
        },
        mockRPC(route, args) {
            if (route === '/longpolling/poll') {
                throw new Error("Can not use the longpolling of the slave client");
            }
            return this._super(...arguments);
        }
    });
    // master
    let pollPromiseMaster = testUtils.makeTestPromise();
    const parentMaster = new Widget();
    testUtils.mock.addMockEnvironment(parentMaster, {
        data: {},
        services: {
            bus_service: this.MockedBusService,
            local_storage: this.makeMockedLocalStorageService(),
        },
        mockRPC(route, args) {
            if (route === '/longpolling/poll') {
                assert.step(`master - ${route} - ${args.channels.join(',')}`);
                pollPromiseMaster = testUtils.makeTestPromise();
                pollPromiseMaster.abort = (function () {
                    this.reject({
                        message: "XmlHttpRequestError abort",
                    }, $.Event());
                }).bind(pollPromiseMaster);
                return pollPromiseMaster;
            }
            return this._super(...arguments);
        }
    });
    const slave = new Widget(parentSlave);
    const master = new Widget(parentMaster);
    master.call('bus_service', 'onNotification', master, notifications =>
        assert.step(`master - notification - ${notifications.toString()}`));
    master.call('bus_service', 'addChannel', 'lambda');
    slave.call('bus_service', 'onNotification', slave, notifications =>
        assert.step(`slave - notification - ${notifications.toString()}`));
    await master.appendTo($('#qunit-fixture'));
    master.call('bus_service', 'testProceedTimeouts');
    await slave.appendTo($('#qunit-fixture'));
    slave.call('bus_service', 'testProceedTimeouts');
    pollPromiseMaster.resolve([{
        id: 1,
        channel: 'lambda',
        message: 'beta',
    }]);
    await testUtils.nextTick();
    assert.verifySteps([
        'master - /longpolling/poll - lambda',
        'master - notification - lambda,beta',
        'master - /longpolling/poll - lambda',
        'slave - notification - lambda,beta',
    ]);

    parentSlave.destroy();
    parentMaster.destroy();
});

QUnit.only('cross tab bus elect new master on master unload', async function (assert) {
    assert.expect(9);

    // slave
    const parentSlave = new Widget();
    let pollPromiseSlave = testUtils.makeTestPromise();
    testUtils.mock.addMockEnvironment(parentSlave, {
        data: {},
        services: {
            bus_service: this.MockedBusService,
            local_storage: this.makeMockedLocalStorageService(),
        },
        mockRPC(route, args) {
            if (route === '/longpolling/poll') {
                assert.step(`slave - ${route} - ${args.channels.join(',')}`);
                pollPromiseSlave = testUtils.makeTestPromise();
                pollPromiseSlave.abort = (function () {
                    this.reject({
                        message: "XmlHttpRequestError abort",
                    }, $.Event());
                }).bind(pollPromiseSlave);
                return pollPromiseSlave;
            }
            return this._super(...arguments);
        }
    });
    // master
    let pollPromiseMaster = testUtils.makeTestPromise();
    const parentMaster = new Widget();
    testUtils.mock.addMockEnvironment(parentMaster, {
        data: {},
        services: {
            bus_service: this.MockedBusService,
            local_storage: this.makeMockedLocalStorageService(),
        },
        mockRPC(route, args) {
            if (route === '/longpolling/poll') {
                assert.step(`master - ${route} - ${args.channels.join(',')}`);
                pollPromiseMaster = testUtils.makeTestPromise();
                pollPromiseMaster.abort = (function () {
                    assert.step(`master - ${route} - abort`);
                    this.reject({
                        message: "XmlHttpRequestError abort",
                    }, $.Event());
                }).bind(pollPromiseMaster);
                return pollPromiseMaster;
            }
            return this._super(...arguments);
        }
    });
    const slave = new Widget(parentSlave);
    const master = new Widget(parentMaster);
    master.call('bus_service', 'onNotification', master, notifications =>
        assert.step(`master - notification - ${notifications.toString()}`));
    master.call('bus_service', 'addChannel', 'lambda');
    slave.call('bus_service', 'onNotification', slave, notifications =>
        assert.step(`slave - notification - ${notifications.toString()}`));
    await master.appendTo($('#qunit-fixture'));
    master.call('bus_service', 'testProceedTimeouts');
    await slave.appendTo($('#qunit-fixture'));
    slave.call('bus_service', 'testProceedTimeouts');
    pollPromiseMaster.resolve([{
        id: 1,
        channel: 'lambda',
        message: 'beta',
    }]);
    await testUtils.nextTick();
    // simulate unloading master
    master.call('bus_service', '_onBeforeunload');
    master.call('bus_service', 'testProceedTimeouts');
    await testUtils.nextTick();
    slave.call('bus_service', 'testProceedTimeouts');
    await testUtils.nextTick();
    slave.call('bus_service', 'testProceedTimeouts');
    await testUtils.nextTick();
    pollPromiseSlave.resolve([{
        id: 2,
        channel: 'lambda',
        message: 'gamma',
    }]);
    slave.call('bus_service', 'testProceedTimeouts');
    await testUtils.nextTick();
    assert.verifySteps([
        'master - /longpolling/poll - lambda',
        'master - notification - lambda,beta',
        'master - /longpolling/poll - lambda',
        'slave - notification - lambda,beta',
        'master - /longpolling/poll - abort',
        'slave - /longpolling/poll - lambda',
        'slave - notification - lambda,gamma',
        'slave - /longpolling/poll - lambda',
    ]);

    parentMaster.destroy();
    parentSlave.destroy();
});

});
});
