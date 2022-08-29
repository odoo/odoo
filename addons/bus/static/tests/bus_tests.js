odoo.define('web.bus_tests', function (require) {
"use strict";

var { busService } = require('@bus/services/bus_service');
const { presenceService } = require('@bus/services/presence_service');
const { multiTabService } = require('@bus/multi_tab_service');
const { WEBSOCKET_CLOSE_CODES } = require("@bus/workers/websocket_worker");
const { startServer } = require('@bus/../tests/helpers/mock_python_environment');
const { patchWebsocketWorkerWithCleanup } = require("@bus/../tests/helpers/mock_websocket");

var testUtils = require('web.test_utils');
const { browser } = require("@web/core/browser/browser");
const { registry } = require("@web/core/registry");
const { makeDeferred, nextTick, patchWithCleanup } = require("@web/../tests/helpers/utils");
const { makeTestEnv } = require('@web/../tests/helpers/mock_env');
const { createWebClient } = require("@web/../tests/webclient/helpers");

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
    QUnit.test('notifications received from the channel', async function (assert) {
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

    QUnit.test('notifications not received after stoping the service', async function (assert) {
        assert.expect(4);

        const pyEnv = await startServer();
        const firstTabEnv = await makeTestEnv({ activateMockServer: true });
        const secondTabEnv = await makeTestEnv({ activateMockServer: true });

        firstTabEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('1 - notification - ' + notifications.map(notif => notif.payload).toString());
        });
        firstTabEnv.services['bus_service'].addChannel('lambda');
        secondTabEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('2 - notification - ' + notifications.map(notif => notif.payload).toString());
        });
        // both tabs should receive the notification
        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'beta');
        await nextTick();
        secondTabEnv.services['bus_service'].stop();
        await nextTick();
        // only first tab should receive the notification since the
        // second tab has called the stop method.
        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'epsilon');
        await nextTick();

        assert.verifySteps([
            '1 - notification - beta',
            '2 - notification - beta',
            '1 - notification - epsilon',
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
        pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
        // Give websocket worker a tick to try to restart
        await nextTick();
        pyEnv['bus.bus']._sendone('lambda', 'notifType', 'gamma');
        // Give bus service a tick to receive the notification from
        // postMessage.
        await nextTick();

        assert.verifySteps([
            "notification - beta",
            "notification - gamma",
        ]);
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
        const slaveEnv = await makeTestEnv();

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
        await nextTick();

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

        const channelPatch = {
            addChannel(channel) {
                assert.step('Tab ' + this.__tabId__ + ': addChannel ' + channel);
                this._super.apply(this, arguments);
            },
            deleteChannel(channel) {
                assert.step('Tab ' + this.__tabId__ + ': deleteChannel ' + channel);
                this._super.apply(this, arguments);
            },
        };
        const firstTabEnv = await makeTestEnv({ activateMockServer: true });
        const secondTabEnv = await makeTestEnv({ activateMockServer: true });
        firstTabEnv.services['bus_service'].__tabId__ = 1;
        secondTabEnv.services['bus_service'].__tabId__ = 2;
        patchWithCleanup(firstTabEnv.services['bus_service'], channelPatch);
        patchWithCleanup(secondTabEnv.services['bus_service'], channelPatch);
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

    QUnit.test('channel management from multiple tabs', async function (assert) {
        assert.expect(4);

        patchWebsocketWorkerWithCleanup({
            _sendToServer({ event_name, data }) {
                assert.step(`${event_name} - [${data.channels.toString()}]`);
            },
        });

        const firstTabEnv = await makeTestEnv();
        const secTabEnv = await makeTestEnv();
        firstTabEnv.services['bus_service'].addChannel('channel1');
        await nextTick();
        // this should not trigger a subscription since the channel1 was
        // aleady known.
        secTabEnv.services['bus_service'].addChannel('channel1');
        await nextTick();
        // removing channel1 from first tab should not trigger
        // re-subscription since the second tab still listens to this
        // channel.
        firstTabEnv.services['bus_service'].deleteChannel('channel1');
        await nextTick();
        // this should trigger a subscription since the channel2 was not
        // known.
        secTabEnv.services['bus_service'].addChannel('channel2');
        await nextTick();

        assert.verifySteps([
            'subscribe - []',
            'subscribe - [channel1]',
            'subscribe - [channel1,channel2]',
        ]);
    });

    QUnit.test('channels subscription after disconnection', async function (assert) {
        // Patch setTimeout in order for the worker to reconnect immediatly.
        patchWithCleanup(window, {
            setTimeout: fn => fn(),
        });
        const worker = patchWebsocketWorkerWithCleanup({
            _sendToServer({ event_name, data }) {
                assert.step(`${event_name} - [${data.channels.toString()}]`);
            },
        });

        await makeTestEnv();
        // wait for the websocket to connect and the first subscription
        // to occur.
        await nextTick();
        worker.websocket.close(WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT);
        // wait for the websocket to re-connect.
        await nextTick();

        assert.verifySteps([
            'subscribe - []',
            'subscribe - []',
        ]);
    });

    QUnit.test('displays reconnect notification', async (assert) => {
        assert.expect(3);

        let startPromise = Promise.resolve();
        patchWebsocketWorkerWithCleanup({
            async _start() {
                const originalStart = this._super;
                await startPromise;
                return originalStart(...arguments);
            },
        });
        const pyEnv = await startServer();
        await createWebClient({});
        // prevent websocket to connect and notification to disappear
        // before the assertion.
        startPromise = makeDeferred();
        pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.ABNORMAL_CLOSURE);
        await nextTick();

        assert.containsOnce(document.body, '.o_notification');
        assert.strictEqual(
            document.querySelector('.o_notification .o_notification_content').textContent,
            'Websocket connection lost. Trying to reconnect...'
        );
        // Wait for the worker to reconnect, post a message and the
        // bus_service to receive it and remove the notification.
        const { afterNextRender } = owl.App;
        startPromise.resolve();
        await afterNextRender(() => {});
        assert.containsNone(document.body, '.o_notification');
    });

    QUnit.test('does not display connection lost popup when refreshing the session', async (assert) => {
        assert.expect(1);

        const pyEnv = await startServer();
        await createWebClient({});
        pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.SESSION_EXPIRED);
        await nextTick();
        assert.containsNone(document.body, '.o_notification');
    });


    QUnit.test('does not display connection lost popup when refreshing the connection upon keep_alive_timeout', async (assert) => {
        assert.expect(1);

        const pyEnv = await startServer();
        await createWebClient({});
        pyEnv.simulateConnectionLost(WEBSOCKET_CLOSE_CODES.KEEP_ALIVE_TIMEOUT);
        await nextTick();
        assert.containsNone(document.body, '.o_notification');
    });
});

});
