odoo.define('web.bus_tests', function (require) {
"use strict";

var { busService } = require('@bus/services/bus_service');
const { presenceService } = require('@bus/services/presence_service');
const { multiTabService } = require('@bus/multi_tab_service');

var { CrossTab } = require('@bus/crosstab_bus');
var testUtils = require('web.test_utils');
const { browser } = require("@web/core/browser/browser");
const { ConnectionLostError } = require("@web/core/network/rpc_service");
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
        assert.expect(6);

        var pollPromise = testUtils.makeTestPromise();
        const env = await makeTestEnv({
            mockRPC(route, args) {
                if (route === '/longpolling/poll') {
                    assert.step(route + ' - ' + args.channels.join(','));

                    pollPromise = testUtils.makeTestPromise();
                    pollPromise.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollPromise);
                    return pollPromise;
                }
            },
        });
        env.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('notification - ' + notifications.toString());
        });
        env.services['bus_service'].addChannel('lambda');

        pollPromise.resolve([{
            message: 'beta',
        }]);
        await testUtils.nextTick();

        pollPromise.resolve([{
            message: 'epsilon',
        }]);
        await testUtils.nextTick();

        assert.verifySteps([
            '/longpolling/poll - lambda',
            'notification - beta',
            '/longpolling/poll - lambda',
            'notification - epsilon',
            '/longpolling/poll - lambda',
        ]);
    });

    QUnit.test('longpolling restarts when connection is lost', async function (assert) {
        assert.expect(4);

        const oldSetTimeout = window.setTimeout;
        patchWithCleanup(
            window,
            {
                setTimeout: callback => oldSetTimeout(callback, 0)
            },
            { pure: true },
        )

        let busService;
        let rpcCount = 0;
        const env = await makeTestEnv({
            mockRPC(route) {
                if (route === '/longpolling/poll') {
                    rpcCount++;
                    assert.step(`polling ${rpcCount}`);
                    if (rpcCount == 1) {
                        return new ConnectionLostError();
                    }
                    assert.equal(rpcCount, 2, "Should not be called after stopPolling");
                    busService.stopPolling();
                    return new ConnectionLostError();
                }
            },
        });
        busService = env.services['bus_service'];
        busService.startPolling();
        // Give longpolling bus a tick to try to restart polling
        await nextTick();

        assert.verifySteps([
            "polling 1",
            "polling 2",
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

    QUnit.test('cross tab bus share message from a channel', async function (assert) {
        assert.expect(5);

        // master

        var pollPromiseMaster = testUtils.makeTestPromise();
        const masterEnv = await makeTestEnv({
            mockRPC(route, args) {
                if (route === '/longpolling/poll') {
                    assert.step('master' + ' - ' + route + ' - ' + args.channels.join(','));

                    pollPromiseMaster = testUtils.makeTestPromise();
                    return pollPromiseMaster;
                }
            }
        });
        masterEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('master - notification - ' + notifications.toString());
        });
        masterEnv.services['bus_service'].addChannel('lambda');

        // slave
        const slaveEnv = await makeTestEnv({
            mockRPC(route, args) {
                if (route === '/longpolling/poll') {
                    throw new Error("Can not use the longpolling of the slave client");
                }
            }
        });
        slaveEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('slave - notification - ' + notifications.toString());
        });
        slaveEnv.services['bus_service'].addChannel('lambda');

        pollPromiseMaster.resolve([{
            id: 1,
            channel: 'lambda',
            message: 'beta',
        }]);
        await testUtils.nextTick();

        assert.verifySteps([
            'master - /longpolling/poll - lambda',
            'master - notification - beta',
            'slave - notification - beta',
            'master - /longpolling/poll - lambda',
        ]);
    });

    QUnit.test('multi tab service elects new master on master unload', async function (assert) {
        assert.expect(8);

        // master
        var pollPromiseMaster = testUtils.makeTestPromise();

        const masterEnv = await makeTestEnv({
            mockRPC(route, args) {
                if (route === '/longpolling/poll') {
                    assert.step('master - ' + route + ' - ' + args.channels.join(','));

                    pollPromiseMaster = testUtils.makeTestPromise();
                    return pollPromiseMaster;
                }
            }
        });

        masterEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('master - notification - ' + notifications.toString());
        });
        masterEnv.services['bus_service'].addChannel('lambda');

        // slave
        var pollPromiseSlave = testUtils.makeTestPromise();
        // prevent slave tab from receiving unload event.
        patchWithCleanup(browser, {
            addEventListener(eventName, callback) {
                if (eventName === 'unload') {
                    return;
                }
                this._super(eventName, callback);
            },
        });
        const slaveEnv = await makeTestEnv({
            mockRPC(route, args) {
                if (route === '/longpolling/poll') {
                    assert.step('slave - ' + route + ' - ' + args.channels.join(','));

                    pollPromiseSlave = testUtils.makeTestPromise();
                    return pollPromiseSlave;
                }
            }
        });
        slaveEnv.services['bus_service'].addEventListener('notification', ({ detail: notifications }) => {
            assert.step('slave - notification - ' + notifications.toString());
        });
        slaveEnv.services['bus_service'].addChannel('lambda');
        pollPromiseMaster.resolve([{
            id: 1,
            channel: 'lambda',
            message: 'beta',
        }]);
        await testUtils.nextTick();

        // simulate unloading master
        window.dispatchEvent(new Event('unload'));

        pollPromiseSlave.resolve([{
            id: 2,
            channel: 'lambda',
            message: 'gamma',
        }]);
        await testUtils.nextTick();

        assert.verifySteps([
            'master - /longpolling/poll - lambda',
            'master - notification - beta',
            'slave - notification - beta',
            'master - /longpolling/poll - lambda',
            'slave - /longpolling/poll - lambda',
            'slave - notification - gamma',
            'slave - /longpolling/poll - lambda',
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

        let pollPromise;
        const firstTabEnv = await makeTestEnv({
            mockRPC(route) {
                if (route === '/longpolling/poll') {
                    pollPromise = testUtils.makeTestPromise();
                    return pollPromise;
                }
            }
        });

        const secondTabEnv = await makeTestEnv({
            mockRPC(route) {
                if (route === '/longpolling/poll') {
                    pollPromise = testUtils.makeTestPromise();
                    return pollPromise;
                }
            }
        });
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
        const firstTabEnv = await makeTestEnv({
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step(args.channels.join());
                    return testUtils.makeTestPromise();
                }
            }
        });
        const secondTabEnv = await makeTestEnv({
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    throw new Error("slave tab should not use the polling route");
                }
            }
        });

        firstTabEnv.services['bus_service'].addChannel("alpha");
        await nextTick();
        assert.verifySteps(["alpha"]);

        secondTabEnv.services['bus_service'].addChannel("beta");
        await nextTick();
        assert.verifySteps(["alpha,beta"]);
    });
});

});
