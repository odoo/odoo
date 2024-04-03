odoo.define('hr_attendance.tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var core = require('web.core');

var MyAttendances = require('hr_attendance.my_attendances');
var KioskMode = require('hr_attendance.kiosk_mode');
var GreetingMessage = require('hr_attendance.greeting_message');


QUnit.module('HR Attendance', {
    beforeEach: function () {
        this.data = {
            'hr.employee': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                    attendance_state: {
                        string: 'State',
                        type: 'selection',
                        selection: [['checked_in', "In"], ['checked_out', "Out"]],
                        default: 1,
                    },
                    user_id: {string: 'user ID', type: 'integer'},
                    barcode: {string:'barcode', type: 'integer'},
                    hours_today: {string:'Hours today', type: 'float'},
                    overtime: {string: 'Overtime', type: 'float'},
                },
                records: [{
                    id: 1,
                    name: "Employee A",
                    attendance_state: 'checked_out',
                    user_id: 1,
                    barcode: 1,
                },
                {
                    id: 2,
                    name: "Employee B",
                    attendance_state: 'checked_out',
                    user_id: 2,
                    barcode: 2,
                }],
            },
            'res.company': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                    attendance_kiosk_mode: {type: 'char'},
                    attendance_barcode_source: {type: 'char'},
                },
                records: [{
                    id: 1,
                    name: "Company A",
                    attendance_kiosk_mode: 'barcode_manual',
                    attendance_barcode_source: 'front',
                }],
            },
        };
    },
}, function () {
    QUnit.module('My attendances (client action)');

    QUnit.test('simple rendering', async function (assert) {
        assert.expect(1);

        var $target = $('#qunit-fixture');
        var clientAction = new MyAttendances(null, {});
        await testUtils.mock.addMockEnvironment(clientAction, {
            data: this.data,
            session: {
                uid: 1,
            },
        });
        await clientAction.appendTo($target);

        assert.strictEqual(clientAction.$('.o_hr_attendance_kiosk_mode h1').text(), 'Employee A',
            "should have rendered the client action without crashing");

        clientAction.destroy();
    });

    QUnit.test('Attendance Kiosk Mode Test', async function (assert) {
        assert.expect(2);

        var $target = $('#qunit-fixture');
        var self = this;
        var rpcCount = 0;
        var clientAction = new KioskMode(null, {});
        await testUtils.mock.addMockEnvironment(clientAction, {
            data: this.data,
            session: {
                uid: 1,
                user_context: {
                    allowed_company_ids: [1],
                }
            },
            mockRPC: function(route, args) {
                if (args.method === 'attendance_scan' && args.model === 'hr.employee') {

                    rpcCount++;
                    return Promise.resolve(self.data['hr.employee'].records[0]);
                }
                return this._super(route, args);
            },
        });
        await clientAction.appendTo($target);
        core.bus.trigger('barcode_scanned', 1);
        core.bus.trigger('barcode_scanned', 1);
        assert.strictEqual(rpcCount, 1, 'RPC call should have been done only once.');

        core.bus.trigger('barcode_scanned', 2);
        assert.strictEqual(rpcCount, 1, 'RPC call should have been done only once.');

        clientAction.destroy();
    });

    QUnit.test('Attendance Greeting Message Test', async function (assert) {
        assert.expect(10);

        var $target = $('#qunit-fixture');
        var self = this;
        var rpcCount = 0;

        var clientActions = [];
        let greetingMessageCreated;
        async function createGreetingMessage (target, barcode){
            var action = {
                attendance: {
                    check_in: "2018-09-20 13:41:13",
                    employee_id: [barcode],
                },
                next_action: "hr_attendance.hr_attendance_action_kiosk_mode",
                barcode: barcode,
            };
            var clientAction = new GreetingMessage(null, action);
            await testUtils.mock.addMockEnvironment(clientAction, {
                data: self.data,
                session: {
                    uid: 1,
                    company_id: 1,
                },
                mockRPC: function(route, args) {
                    if (args.method === 'attendance_scan' && args.model === 'hr.employee') {
                        rpcCount++;
                        action.attendance.employee_id = [args.args[0], 'Employee'];
                        /*
                            if rpc have been made, a new instance is created to simulate the same behaviour
                            as functional flow.
                        */
                        greetingMessageCreated = createGreetingMessage (target, args.args[0]);
                        return Promise.resolve({action: action});
                    }
                    return this._super(route, args);
                },
            });
            await clientAction.appendTo(target);

            clientActions.push(clientAction);
        }

        // init - mock coming from kiosk
        await createGreetingMessage ($target, 1);
        await testUtils.nextMicrotaskTick();
        assert.strictEqual(clientActions.length, 1, 'Number of clientAction must = 1.');

        core.bus.trigger('barcode_scanned', 1);
        /*
            As action is given when instantiate GreetingMessage, we simulate that we come from the KioskMode
            So rescanning the same barcode won't lead to another RPC.
        */
        assert.strictEqual(clientActions.length, 1, 'Number of clientActions must = 1.');
        assert.strictEqual(rpcCount, 0, 'RPC call should not have been done.');

        core.bus.trigger('barcode_scanned', 2);
        await greetingMessageCreated;
        assert.strictEqual(clientActions.length, 2, 'Number of clientActions must = 2.');
        assert.strictEqual(rpcCount, 1, 'RPC call should have been done only once.');
        core.bus.trigger('barcode_scanned', 2);
        await testUtils.nextMicrotaskTick();
        assert.strictEqual(clientActions.length, 2, 'Number of clientActions must = 2.');
        assert.strictEqual(rpcCount, 1, 'RPC call should have been done only once.');

        core.bus.trigger('barcode_scanned', 1);
        await greetingMessageCreated;
        assert.strictEqual(clientActions.length, 3, 'Number of clientActions must = 3.');
        core.bus.trigger('barcode_scanned', 1);
        await testUtils.nextMicrotaskTick();
        assert.strictEqual(clientActions.length, 3, 'Number of clientActions must = 3.');
        assert.strictEqual(rpcCount, 2, 'RPC call should have been done only twice.');

        _.each(clientActions.reverse(), function(clientAction) {
            clientAction.destroy();
        });
    });

});

});
