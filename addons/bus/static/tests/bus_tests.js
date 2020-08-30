odoo.define('web.bus_tests', function (require) {
"use strict";

var BusService = require('bus.BusService');
var AbstractStorageService = require('web.AbstractStorageService');
var RamStorage = require('web.RamStorage');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');


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
            'master - notification - lambda,beta',
            'slave - notification - lambda,beta',
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
            'master - notification - lambda,beta',
            'slave - notification - lambda,beta',
            'master - /longpolling/poll - lambda',
            'slave - /longpolling/poll - lambda',
            'slave - notification - lambda,gamma',
            'slave - /longpolling/poll - lambda',
        ]);

        parentMaster.destroy();
        parentSlave.destroy();
    });
});
});
