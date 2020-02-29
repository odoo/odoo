odoo.define('hr_holidays.leave_stats_widget_tests', function (require) {
    "use strict";

    var FormView = require("web.FormView");
    var testUtils = require('web.test_utils');

    var createView = testUtils.createView;

    QUnit.module('leave_stats_widget', {
        beforeEach: function () {
            this.data = {
                department: {
                    fields: {
                        name: { string: "Name", type: "char" },
                    },
                    records: [{id:11, name: "R&D"}],
                },
                employee: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        department_id: { string: "Department", type: "many2one", relation: 'department' },
                    },
                    records: [{
                        id: 100,
                        name: "Richard",
                        department_id: 11,
                    },{
                        id: 200,
                        name: "Jesus",
                        department_id: 11,
                    }],
                },
                'hr.leave.type': {
                    fields: {
                        name: { string: "Name", type: "char" }
                    },
                    records: [{
                        id: 55,
                        name: "Legal Leave",
                    }]
                },
                'hr.leave': {
                    fields: {
                        employee_id: { string: "Employee", type: "many2one", relation: 'employee' },
                        department_id: { string: "Department", type: "many2one", relation: 'department' },
                        date_from: { string: "From", type: "datetime" },
                        date_to: { string: "To", type: "datetime" },
                        holiday_status_id: { string: "Leave type", type: "many2one", relation: 'hr.leave.type' },
                        state: { string: "State", type: "char" },
                        holiday_type: { string: "Holiday Type", type: "char" },
                        number_of_days: { string: "State", type: "integer" },
                    },
                    records: [{
                        id: 12,
                        employee_id: 100,
                        department_id: 11,
                        date_from: "2016-10-20 09:00:00",
                        date_to:  "2016-10-25 18:00:00",
                        holiday_status_id: 55,
                        state: 'validate',
                        number_of_days: 5,
                        holiday_type: 'employee',
                    },{
                        id: 13,
                        employee_id: 100,
                        department_id: 11,
                        date_from: "2016-10-2 09:00:00",
                        date_to:  "2016-10-2 18:00:00",
                        holiday_status_id: 55,
                        state: 'validate',
                        number_of_days: 1,
                        holiday_type: 'employee',
                    },{
                        id: 14,
                        employee_id: 200,
                        department_id: 11,
                        date_from:  "2016-10-15 09:00:00",
                        date_to:  "2016-10-20 18:00:00",
                        holiday_status_id: 55,
                        state: 'validate',
                        number_of_days: 8,
                        holiday_type: 'employee',
                    }]
                }
            };
        }
    }, function () {
        QUnit.test('leave stats renders correctly', async function (assert) {
            assert.expect(5);
            var self = this;
            var form = await createView({
                View: FormView,
                model: 'hr.leave',
                data: this.data,
                arch: '<form string="Leave">' +
                    '<field name="employee_id"/>' +
                    '<field name="department_id"/>' +
                    '<field name="date_from"/>' +
                    '<widget name="hr_leave_stats"/>' +
                '</form>',
                res_id: 12,
                mockRPC: function (route, args) {
                    if (args.model === 'hr.leave' && args.method === 'search') {
                        return Promise.resolve(self.data['hr.leave'].records.map(function (record) { return record.id; }));
                    }
                    return this._super.apply(this, arguments);
                },
            });
            var $leaveTypeBody = form.$('.o_leave_stats table:first > tbody');
            var $leavesDepartmentBody = form.$('.o_leave_stats table:nth-child(2) > tbody');
            var $leavesDepartmentHeader = form.$('.o_leave_stats table:nth-child(2) > thead');

            assert.strictEqual($leaveTypeBody.find('td:contains(Legal Leave)').length, 1, "it should have leave type");
            assert.strictEqual($leaveTypeBody.find('td:contains(6)').length, 1, "it should have 6 days");

            assert.strictEqual($leavesDepartmentBody.find('td:contains(Richard)').length, 2, "it should have 2 leaves for Richard");
            assert.strictEqual($leavesDepartmentBody.find('td:contains(Jesus)').length, 1, "it should have 1 leaves for Jesus");
            assert.strictEqual($leavesDepartmentHeader.find('td:contains(R&D)').length, 1, "it should have R&D title");
            form.destroy();
        });
        QUnit.test('leave stats reload when employee/department changes', async function (assert) {
            assert.expect(2);
            var form = await createView({
                View: FormView,
                model: 'hr.leave',
                mode: 'edit',
                data: this.data,
                arch: '<form string="Leave">' +
                    '<field name="employee_id"/>' +
                    '<field name="department_id"/>' +
                    '<field name="date_from"/>' +
                    '<widget name="hr_leave_stats"/>' +
                '</form>',
                mockRPC: function (route, args) {
                    if (args.model === 'hr.leave' && args.method === 'search_read') {
                        assert.ok(_.some(args.args[0], ['department_id', '=', 11]), "It should load department's leaves data");
                    }
                    if (args.model === 'hr.leave' && args.method === 'read_group') {
                        assert.ok(_.some(args.kwargs.domain, ['employee_id', '=', 200]), "It should load employee's leaves data");
                    }
                    return this._super.apply(this, arguments);
                },
            });
            // Set date => shouldn't load data yet (no employee nor department defined)
            await testUtils.fields.editSelect($('input[name="date_from"]'), '2016-10-12 09:00:00');
            // Set employee => should load employee's date
            await testUtils.fields.many2one.clickOpenDropdown("employee_id");
            await testUtils.fields.many2one.clickItem("employee_id", "Jesus");
            // Set department => should load department's data
            await testUtils.fields.many2one.clickOpenDropdown("department_id");
            await testUtils.fields.many2one.clickItem("department_id", "R&D");

            form.destroy();
        });
    });
});
