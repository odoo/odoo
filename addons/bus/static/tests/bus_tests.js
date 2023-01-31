odoo.define('web.bus_tests', function (require) {
"use strict";

var BusService = require('bus.BusService');
var CrossTabBus = require('bus.CrossTab');
var AbstractStorageService = require('web.AbstractStorageService');
var RamStorage = require('web.RamStorage');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
const LegacyRegistry = require("web.Registry");
const { ConnectionLostError } = require("@web/core/network/rpc_service");
const { patchWithCleanup, nextTick } = require("@web/../tests/helpers/utils");
const { createWebClient } =  require('@web/../tests/webclient/helpers');


var LocalStorageServiceMock;

BusService = BusService.extend({
    TAB_HEARTBEAT_PERIOD: 10,
    MASTER_TAB_HEARTBEAT_PERIOD: 1,
});


QUnit.module('Bus', {
    beforeEach: function () {
        LocalStorageServiceMock = AbstractStorageService.extend({storage: new RamStorage()});
    },
}, function () {
    QUnit.test('notifications received from the longpolling channel', async function (assert) {
        assert.expect(6);

        var pollPromise = testUtils.makeTestPromise();

        var parent = new Widget();
        await testUtils.mock.addMockEnvironment(parent, {
            data: {},
            services: {
                bus_service: BusService,
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step(route + ' - ' + args.channels.join(','));

                    pollPromise = testUtils.makeTestPromise();
                    pollPromise.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollPromise);
                    return pollPromise;
                }
                return this._super.apply(this, arguments);
            }
        });

        var widget = new Widget(parent);
        await widget.appendTo($('#qunit-fixture'));

        widget.call('bus_service', 'onNotification', this, function (notifications) {
            assert.step('notification - ' + notifications.toString());
        });
        widget.call('bus_service', 'addChannel', 'lambda');

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

        parent.destroy();
    });

    QUnit.test('longpolling restarts when connection is lost', async function (assert) {
        assert.expect(4);
        const legacyRegistry = new LegacyRegistry();
        legacyRegistry.add("bus_service", BusService);
        legacyRegistry.add("local_storage", LocalStorageServiceMock);

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
        // Using createWebclient to get the compatibility layer between the old services and the new
        await createWebClient({
            mockRPC(route) {
                if (route === '/longpolling/poll') {
                    rpcCount++;
                    assert.step(`polling ${rpcCount}`);
                    if (rpcCount == 1) {
                        return Promise.reject(new ConnectionLostError());
                    }
                    assert.equal(rpcCount, 2, "Should not be called after stopPolling");
                    busService.stopPolling();
                    return Promise.reject(new ConnectionLostError());
                }
            },
            legacyParams: { serviceRegistry: legacyRegistry },
        });
        busService = owl.Component.env.services.bus_service;
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
        testUtils.mock.patch(LocalStorageServiceMock, {
            getItem: function (key) {
                if (key === 'last_ts') {
                    return 0;
                }
                return this._super.apply(this, arguments);
            },
        });

        var pollPromise = testUtils.makeTestPromise();
        var parent = new Widget();
        await testUtils.mock.addMockEnvironment(parent, {
            data: {},
            services: {
                bus_service: BusService,
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step(route);
                    assert.strictEqual(args.last, 0,
                        "provided last notification ID should be 0");

                    pollPromise = testUtils.makeTestPromise();
                    pollPromise.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollPromise);
                    return pollPromise;
                }
                return this._super.apply(this, arguments);
            }
        });

        var widget = new Widget(parent);
        await widget.appendTo($('#qunit-fixture'));

        // trigger longpolling poll RPC
        widget.call('bus_service', 'addChannel', 'lambda');
        assert.verifySteps(['/longpolling/poll']);

        testUtils.mock.unpatch(LocalStorageServiceMock);
        parent.destroy();
    });

    QUnit.test('cross tab bus share message from a channel', async function (assert) {
        assert.expect(5);

        // master

        var pollPromiseMaster = testUtils.makeTestPromise();

        var parentMaster = new Widget();
        await testUtils.mock.addMockEnvironment(parentMaster, {
            data: {},
            services: {
                bus_service: BusService,
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step('master' + ' - ' + route + ' - ' + args.channels.join(','));

                    pollPromiseMaster = testUtils.makeTestPromise();
                    pollPromiseMaster.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollPromiseMaster);
                    return pollPromiseMaster;
                }
                return this._super.apply(this, arguments);
            }
        });

        var master = new Widget(parentMaster);
        await master.appendTo($('#qunit-fixture'));

        master.call('bus_service', 'onNotification', master, function (notifications) {
            assert.step('master - notification - ' + notifications.toString());
        });
        master.call('bus_service', 'addChannel', 'lambda');

        // slave
        await testUtils.nextTick();
        var parentSlave = new Widget();
        await testUtils.mock.addMockEnvironment(parentSlave, {
            data: {},
            services: {
                bus_service: BusService,
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    throw new Error("Can not use the longpolling of the slave client");
                }
                return this._super.apply(this, arguments);
            }
        });

        var slave = new Widget(parentSlave);
        await slave.appendTo($('#qunit-fixture'));

        slave.call('bus_service', 'onNotification', slave, function (notifications) {
            assert.step('slave - notification - ' + notifications.toString());
        });
        slave.call('bus_service', 'addChannel', 'lambda');

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

        parentMaster.destroy();
        parentSlave.destroy();
    });

    QUnit.test('cross tab bus elect new master on master unload', async function (assert) {
        assert.expect(8);

        // master
        var pollPromiseMaster = testUtils.makeTestPromise();

        var parentMaster = new Widget();
        await testUtils.mock.addMockEnvironment(parentMaster, {
            data: {},
            services: {
                bus_service: BusService,
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step('master - ' + route + ' - ' + args.channels.join(','));

                    pollPromiseMaster = testUtils.makeTestPromise();
                    pollPromiseMaster.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollPromiseMaster);
                    return pollPromiseMaster;
                }
                return this._super.apply(this, arguments);
            }
        });

        var master = new Widget(parentMaster);
        await master.appendTo($('#qunit-fixture'));

        master.call('bus_service', 'onNotification', master, function (notifications) {
            assert.step('master - notification - ' + notifications.toString());
        });
        master.call('bus_service', 'addChannel', 'lambda');

        // slave
        await testUtils.nextTick();
        var parentSlave = new Widget();
        var pollPromiseSlave = testUtils.makeTestPromise();
        await testUtils.mock.addMockEnvironment(parentSlave, {
            data: {},
            services: {
                bus_service: BusService,
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step('slave - ' + route + ' - ' + args.channels.join(','));

                    pollPromiseSlave = testUtils.makeTestPromise();
                    pollPromiseSlave.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollPromiseSlave);
                    return pollPromiseSlave;
                }
                return this._super.apply(this, arguments);
            }
        });

        var slave = new Widget(parentSlave);
        await slave.appendTo($('#qunit-fixture'));

        slave.call('bus_service', 'onNotification', slave, function (notifications) {
            assert.step('slave - notification - ' + notifications.toString());
        });
        slave.call('bus_service', 'addChannel', 'lambda');

        pollPromiseMaster.resolve([{
            id: 1,
            channel: 'lambda',
            message: 'beta',
        }]);
        await testUtils.nextTick();

        // simulate unloading master
        master.call('bus_service', '_onUnload');

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

        parentMaster.destroy();
        parentSlave.destroy();
    });

    QUnit.test('two tabs calling addChannel simultaneously', async function (assert) {
        assert.expect(5);

        let id = 1;
        testUtils.mock.patch(CrossTabBus, {
            init: function () {
                this._super.apply(this, arguments);
                this.__tabId__ = id++;
            },
            addChannel: function (channel) {
                assert.step('Tab ' + this.__tabId__ + ': addChannel ' + channel);
                this._super.apply(this, arguments);
            },
            deleteChannel: function (channel) {
                assert.step('Tab ' + this.__tabId__ + ': deleteChannel ' + channel);
                this._super.apply(this, arguments);
            },
        });

        let pollPromise;
        const parentTab1 = new Widget();
        await testUtils.mock.addMockEnvironment(parentTab1, {
            data: {},
            services: {
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route) {
                if (route === '/longpolling/poll') {
                    pollPromise = testUtils.makeTestPromise();
                    pollPromise.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollPromise);
                    return pollPromise;
                }
                return this._super.apply(this, arguments);
            }
        });
        const parentTab2 = new Widget();
        await testUtils.mock.addMockEnvironment(parentTab2, {
            data: {},
            services: {
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route) {
                if (route === '/longpolling/poll') {
                    pollPromise = testUtils.makeTestPromise();
                    pollPromise.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollPromise);
                    return pollPromise;
                }
                return this._super.apply(this, arguments);
            }
        });

        const tab1 = new CrossTabBus(parentTab1);
        const tab2 = new CrossTabBus(parentTab2);

        tab1.addChannel("alpha");
        tab2.addChannel("alpha");
        tab1.addChannel("beta");
        tab2.addChannel("beta");

        assert.verifySteps([
            "Tab 1: addChannel alpha",
            "Tab 2: addChannel alpha",
            "Tab 1: addChannel beta",
            "Tab 2: addChannel beta",
        ]);

        testUtils.mock.unpatch(CrossTabBus);
        parentTab1.destroy();
        parentTab2.destroy();
    });

    QUnit.test('two tabs adding channels', async function (assert) {
        assert.expect(4);
        const parentTab1 = new Widget();
        let pollPromise;
        await testUtils.mock.addMockEnvironment(parentTab1, {
            data: {},
            services: {
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step(args.channels.join())
                    pollPromise = testUtils.makeTestPromise();
                    pollPromise.abort = (function () {
                        this.reject({message: 'XmlHttpRequestError abort'});
                    }).bind(pollPromise);
                    return pollPromise;
                }
                return this._super.apply(this, arguments);
            }
        });
        const parentTab2 = new Widget();
        await testUtils.mock.addMockEnvironment(parentTab2, {
            data: {},
            services: {
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    throw new Error("slave tab should not use the polling route")
                }
                return this._super.apply(this, arguments);
            }
        });

        const tab1 = new CrossTabBus(parentTab1);
        const tab2 = new CrossTabBus(parentTab2);
        tab1.addChannel("alpha");
        await nextTick();
        assert.verifySteps(["alpha"]);

        tab2.addChannel("beta");
        await nextTick();
        assert.verifySteps(["alpha,beta"]);

        parentTab1.destroy();
        parentTab2.destroy();
    });
});

});
