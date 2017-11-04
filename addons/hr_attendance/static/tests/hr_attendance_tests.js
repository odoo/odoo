odoo.define('hr_attendance.tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');

var MyAttendances = require('hr_attendance.my_attendances');


QUnit.module('HR Attendance', {
    beforeEach: function () {
        this.data = {
            'hr.employee': {
                fields: {
                    name: {string: 'Name', type: 'char'},
                    attendance_state: {
                        string: 'State',
                        type: 'selection',
                        selection: [[1, "In"], [2, "Out"]],
                        default: 1,
                    },
                    user_id: {string: 'user ID', type: 'integer'},
                },
                records: [{
                    id: 1,
                    name: "Employee A",
                    attendance_state: 1,
                    user_id: 1,
                }],
            },
        };
    },
}, function () {
    QUnit.module('My attendances (client action)');

    QUnit.test('simple rendering', function (assert) {
        assert.expect(1);

        var $target = $('#qunit-fixture');
        var clientAction = new MyAttendances(null);
        testUtils.addMockEnvironment(clientAction, {
            data: this.data,
            session: {
                uid: 1,
            },
        });
        clientAction.appendTo($target);

        assert.strictEqual(clientAction.$('.o_hr_attendance_kiosk_mode h1').text(), 'Welcome Employee A',
            "should have rendered the client action without crashing");

        clientAction.destroy();
    });

});

});
