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
    QUnit.test('notifications received from the longpolling channel', function (assert) {
        assert.expect(6);

        var pollDeferred = $.Deferred();

        var parent = new Widget();
        testUtils.addMockEnvironment(parent, {
            data: {},
            services: {
                bus_service: BusService,
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step([route, args.channels.join(',')]);

                    pollDeferred = $.Deferred();
                    pollDeferred.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollDeferred);
                    return pollDeferred;
                }
                return this._super.apply(this, arguments);
            }
        });

        var widget = new Widget(parent);
        widget.appendTo($('#qunit-fixture'));

        widget.call('bus_service', 'onNotification', this, function (notifications) {
            assert.step(['notification', notifications]);
        });
        widget.call('bus_service', 'addChannel', 'lambda');

        pollDeferred.resolve([{
            id: 1,
            channel: 'lambda',
            message: 'beta',
        }]);
        pollDeferred.resolve([{
            id: 2,
            channel: 'lambda',
            message: 'epsilon',
        }]);

        assert.verifySteps([
            ["/longpolling/poll", "lambda"],
            ["notification", [["lambda","beta"]]],
            ["/longpolling/poll", "lambda"],
            ["notification", [["lambda","epsilon"]]],
            ["/longpolling/poll", "lambda"]
        ]);

        parent.destroy();
    });

    QUnit.test('cross tab bus share message from a channel', function (assert) {
        var done = assert.async();
        assert.expect(5);

        // master

        var pollDeferredMaster = $.Deferred();

        var parentMaster = new Widget();
        testUtils.addMockEnvironment(parentMaster, {
            data: {},
            services: {
                bus_service: BusService,
                local_storage: LocalStorageServiceMock,
            },
            mockRPC: function (route, args) {
                if (route === '/longpolling/poll') {
                    assert.step(['master', route, args.channels.join(',')]);

                    pollDeferredMaster = $.Deferred();
                    pollDeferredMaster.abort = (function () {
                        this.reject({message: "XmlHttpRequestError abort"}, $.Event());
                    }).bind(pollDeferredMaster);
                    return pollDeferredMaster;
                }
                return this._super.apply(this, arguments);
            }
        });

        var master = new Widget(parentMaster);
        master.appendTo($('#qunit-fixture'));

        master.call('bus_service', 'onNotification', master, function (notifications) {
            assert.step(['master', 'notification', notifications]);
        });
        master.call('bus_service', 'addChannel', 'lambda');

        // slave

        setTimeout(function () {
            var parentSlave = new Widget();
            testUtils.addMockEnvironment(parentSlave, {
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
            slave.appendTo($('#qunit-fixture'));

            slave.call('bus_service', 'onNotification', slave, function (notifications) {
                assert.step(['slave', 'notification', notifications]);
            });
            slave.call('bus_service', 'addChannel', 'lambda');

            pollDeferredMaster.resolve([{
                id: 1,
                channel: 'lambda',
                message: 'beta',
            }]);

            assert.verifySteps([
                ["master", "/longpolling/poll", "lambda"],
                ["master", "notification", [["lambda", "beta"]]],
                ["slave", "notification", [["lambda", "beta"]]],
                ["master", "/longpolling/poll", "lambda"],
            ]);

            parentMaster.destroy();
            parentSlave.destroy();

            done();

        }, 3);
    });
});});
