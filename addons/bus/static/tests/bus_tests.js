odoo.define('web.bus_tests', function (require) {
"use strict";

var { busService } = require('@bus/services/bus_service');
const { startServer } = require('@bus/../tests/helpers/mock_python_environment');
const { presenceService } = require('@bus/services/presence_service');
const { multiTabService } = require('@bus/multi_tab_service');

var { CrossTab } = require('@bus/crosstab_bus');
var testUtils = require('web.test_utils');
const { browser } = require("@web/core/browser/browser");
const { registry } = require("@web/core/registry");
const { patchWithCleanup, nextTick } = require("@web/../tests/helpers/utils");
const { makeTestEnv } = require('@web/../tests/helpers/mock_env');

QUnit.module('Bus', {
    beforeEach: function () {
        const customMultiTabService = {
            ...multiTabService,
            start() {
                const originalMultiTabService = multiTabService.start(...arguments);
                originalMultiTabService.TAB_HEARTBEAT_PERIOD = 10;
                originalMultiTabService.MAIN_TAB_HEARTBEAT_PERIOD = 1;
                return originalMultiTabService;
            },
        };
        registry.category('services').add('bus_service', busService);
        registry.category('services').add('presence', presenceService);
        registry.category('services').add('multi_tab', customMultiTabService);
    },
}, function () {
    QUnit.test('notifications received from the longpolling channel', async function (assert) {
        assert.expect(3);

        const pyEnv = await startServer();
        const env = await makeTestEnv({ activateMockServer: true });
        env.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('notification - ' + notifications.map(notif => notif.payload).toString());
        });
        env.services['bus_service'].addChannel('lambda');
        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'beta');
        await testUtils.nextTick();

        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'epsilon');
        await testUtils.nextTick();

        assert.verifySteps([
            'notification - beta',
            'notification - epsilon',
        ]);
    });

    QUnit.test('notifications still received after disconnect/reconnect', async function (assert) {
        assert.expect(3);

        const oldSetTimeout = window.setTimeout;
        patchWithCleanup(
            window,
            {
                setTimeout: callback => oldSetTimeout(callback, 0)
            },
            { pure: true },
        )

        const pyEnv = await startServer();
        const env = await makeTestEnv({ activateMockServer: true });
        env.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('notification - ' + notifications.map(notif => notif.payload).toString());
        });
        env.services['bus_service'].addChannel('lambda');
        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'beta');
        pyEnv.simulateConnectionLostAndRecovered();
        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'gamma');
        // Give longpolling bus a tick to try to restart polling
        await nextTick();

        assert.verifySteps([
            "notification - beta",
            "notification - gamma",
        ]);
    });

    QUnit.test('provide notification ID of 0 by default', async function (assert) {
        // This test is important in order to ensure that we provide the correct
        // sentinel value 0 when we are not aware of the last notification ID
        // that we have received. We cannot provide an ID of -1, otherwise it
        // may likely be handled incorrectly (before this test was written,
        // it was providing -1 to the server, which in return sent every stored
        // notifications related to this user).
        assert.expect(3);

        // Simulate no ID of last notification in the local storage
        patchWithCleanup(browser, {
            getItem(key) {
                if (key === 'last_ts') {
                    return 0;
                }
                return this._super(...arguments);
            },
        });

        var pollPromise = testUtils.makeTestPromise();
        const env = await makeTestEnv({
            mockRPC(route, args) {
                if (route === '/longpolling/poll') {
                    assert.step(route);
                    assert.strictEqual(args.last, 0,
                        "provided last notification ID should be 0");

                    pollPromise = testUtils.makeTestPromise();
                    return pollPromise;
                }
            }
        });

        // trigger longpolling poll RPC
        env.services['bus_service'].addChannel('lambda');
        assert.verifySteps(['/longpolling/poll']);
    });

    QUnit.test('tabs share message from a channel', async function (assert) {
        assert.expect(3);

        const pyEnv = await startServer();
        // main
        const mainEnv = await makeTestEnv({ activateMockServer: true });
        mainEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('main - notification - ' + notifications.map(notif => notif.payload).toString());
        });
        mainEnv.services['bus_service'].addChannel('lambda');

        // slave
        const slaveEnv = await makeTestEnv({
            mockRPC(route, args) {
                if (route === '/longpolling/poll') {
                    throw new Error("Can not use the longpolling of the slave client");
                }
            }
        });
        slaveEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('slave - notification - ' + notifications.map(notif => notif.payload).toString());
        });
        slaveEnv.services['bus_service'].addChannel('lambda');

        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'beta');
        await testUtils.nextTick();

        assert.verifySteps([
            'main - notification - beta',
            'slave - notification - beta',
        ]);
    });

    QUnit.test('secondEnv start polling after main unload', async function (assert) {
        assert.expect(3);

        // main tab.
        const mainEnv = await makeTestEnv({
            mockRPC(route) {
                if (route === '/longpolling/poll') {
                    assert.step('main - poll');
                }
            }
        });
        // prevent second tab from receiving unload event.
        patchWithCleanup(browser, {
            addEventListener(eventName, callback) {
                if (eventName === 'unload') {
                    return;
                }
                this._super(eventName, callback);
            },
        });
        // second tab
        await makeTestEnv({
            mockRPC(route) {
                if (route === '/longpolling/poll') {
                    assert.step('second - poll');
                }
            }
        });
        mainEnv.services['bus_service'].startPolling();
        // simulate main unload.
        window.dispatchEvent(new Event('unload'));

        assert.verifySteps([
            'main - poll',
            'second - poll',
        ]);
    });

    QUnit.test('second tab still receives notifications after main unload', async function (assert) {
        assert.expect(4);

        const pyEnv = await startServer();
        // main
        const mainEnv = await makeTestEnv({ activateMockServer: true });
        mainEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('main - notification - ' + notifications.map(notif => notif.payload).toString());
        });
        mainEnv.services['bus_service'].addChannel('lambda');

        // second env
        // prevent second tab from receiving unload event.
        patchWithCleanup(browser, {
            addEventListener(eventName, callback) {
                if (eventName === 'unload') {
                    return;
                }
                this._super(eventName, callback);
            },
        });
        const secondEnv = await makeTestEnv({ activateMockServer: true });
        secondEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('slave - notification - ' + notifications.map(notif => notif.payload).toString());
        });
        secondEnv.services['bus_service'].addChannel('lambda');
        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'beta');
        await testUtils.nextTick();

        // simulate unloading main
        window.dispatchEvent(new Event('unload'));

        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'gamma');
        await testUtils.nextTick();

        assert.verifySteps([
            'main - notification - beta',
            'slave - notification - beta',
            'slave - notification - gamma',
        ]);
    });

    QUnit.test('two tabs calling addChannel simultaneously', async function (assert) {
        assert.expect(5);

        patchWithCleanup(CrossTab.prototype, {
            addChannel(channel) {
                assert.step('Tab ' + this.__tabId__ + ': addChannel ' + channel);
                this._super.apply(this, arguments);
            },
            deleteChannel(channel) {
                assert.step('Tab ' + this.__tabId__ + ': deleteChannel ' + channel);
                this._super.apply(this, arguments);
            },
        });

        const firstTabEnv = await makeTestEnv({ activateMockServer: true });
        const secondTabEnv = await makeTestEnv({ activateMockServer: true });
        firstTabEnv.services['bus_service'].__tabId__ = 1;
        secondTabEnv.services['bus_service'].__tabId__ = 2;
        firstTabEnv.services['bus_service'].addChannel('alpha');
        secondTabEnv.services['bus_service'].addChannel('alpha');
        firstTabEnv.services['bus_service'].addChannel('beta');
        secondTabEnv.services['bus_service'].addChannel('beta');

        assert.verifySteps([
            "Tab 1: addChannel alpha",
            "Tab 2: addChannel alpha",
            "Tab 1: addChannel beta",
            "Tab 2: addChannel beta",
        ]);
    });

    QUnit.test('two tabs adding a different channel', async function (assert) {
        assert.expect(3);

        const pyEnv = await startServer();
        const firstTabEnv = await makeTestEnv({ activateMockServer: true });
        const secondTabEnv = await makeTestEnv({ activateMockServer: true });
        firstTabEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('first - notification - ' + notifications.map(notif => notif.payload).toString());
        });
        secondTabEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('second - notification - ' + notifications.map(notif => notif.payload).toString());
        });
        firstTabEnv.services['bus_service'].addChannel("alpha");
        secondTabEnv.services['bus_service'].addChannel("beta");
        await nextTick();
        pyEnv['bus.bus']._sendmany([
            ['alpha', 'notifType', 'alpha'],
            ['beta', 'notifType', 'beta']
        ]);
        await nextTick();

        assert.verifySteps([
            'first - notification - alpha,beta',
            'second - notification - alpha,beta',
        ]);
    });
});

});
