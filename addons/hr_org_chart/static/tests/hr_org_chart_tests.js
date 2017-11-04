odoo.define('hr_org_chart.tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require("web.test_utils");

var createView = testUtils.createView;

QUnit.module('hr_org_chart', {
    before: function () {
        this.data = {
            hr_employee: {
                fields: {
                    child_ids: {string: "one2many Subordinates field", type: "one2many", relation: 'hr_employee'},
                },
                records: [{
                    id: 1,
                    child_ids: [],
                }]
            }
        };
    },
}, function () {
    QUnit.test("hr org chart: empty render", function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'hr_employee',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="child_ids" widget="hr_org_chart"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/hr/get_org_chart') {
                    assert.ok('employee_id' in args, "it should have 'employee_id' as argument");
                    return $.when({
                        children: [],
                        managers: [],
                        managers_more: false,
                    });
                }
                return this._super(route, args);
            }
        });
        assert.strictEqual(form.$('[name="child_ids"]').children().length, 1, "the chart should have 1 child");
        form.destroy();
    });
    QUnit.test("hr org chart: basic render", function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'hr_employee',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<div id="o_employee_container"><div id="o_employee_main">' +
                            '<div id="o_employee_right">' +
                                '<field name="child_ids" widget="hr_org_chart"/>' +
                            '</div>' +
                        '</div></div>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/hr/get_org_chart') {
                    assert.ok('employee_id' in args, "it should have 'employee_id' as argument");
                    return $.when({
                        children: [{
                            direct_sub_count: 0,
                            indirect_sub_count: 0,
                            job_id: 2,
                            job_name: 'Sub-Gooroo',
                            link: 'fake_link',
                            name: 'Michael Hawkins',
                        }],
                        managers: [],
                        managers_more: false,
                        self: {
                            direct_sub_count: 1,
                            id: 1,
                            indirect_sub_count: 1,
                            job_id: 1,
                            job_name: 'Gooroo',
                            link: 'fake_link',
                            name: 'Antoine Langlais',
                        }
                    });
                }
                return this._super(route, args);
            }
        });
        assert.strictEqual(form.$('.o_org_chart_entry_sub').length, 1,
            "the chart should have 1 subordinate");
        assert.strictEqual(form.$('.o_org_chart_entry_self').length, 1,
            "the current employee should only be displayed once in the chart");
        form.destroy();
    });
    QUnit.test("hr org chart: basic manager render", function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'hr_employee',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<div id="o_employee_container"><div id="o_employee_main">' +
                            '<div id="o_employee_right">' +
                                '<field name="child_ids" widget="hr_org_chart"/>' +
                            '</div>' +
                        '</div></div>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/hr/get_org_chart') {
                    assert.ok('employee_id' in args, "should have 'employee_id' as argument");
                    return $.when({
                        children: [{
                            direct_sub_count: 0,
                            indirect_sub_count: 0,
                            job_id: 2,
                            job_name: 'Sub-Gooroo',
                            link: 'fake_link',
                            name: 'Michael Hawkins',
                        }],
                        managers: [{
                            direct_sub_count: 1,
                            id: 1,
                            indirect_sub_count: 2,
                            job_id: 1,
                            job_name: 'Chief Gooroo',
                            link: 'fake_link',
                            name: 'Antoine Langlais',
                        }],
                        managers_more: false,
                        self: {
                            direct_sub_count: 1,
                            id: 1,
                            indirect_sub_count: 1,
                            job_id: 3,
                            job_name: 'Gooroo',
                            link: 'fake_link',
                            name: 'John Smith',
                        }
                    });
                }
                return this._super(route, args);
            }
        });
        assert.strictEqual(form.$('.o_org_chart_group_up .o_org_chart_entry_manager').length, 1, "the chart should have 1 manager");
        assert.strictEqual(form.$('.o_org_chart_group_down .o_org_chart_entry_sub').length, 1, "the chart should have 1 subordinate");
        assert.strictEqual(form.$('.o_org_chart_entry_self').length, 1, "the chart should have only once the current employee");
        form.destroy();
    });
});

});