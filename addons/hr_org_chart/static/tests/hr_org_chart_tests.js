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
    QUnit.test("hr org chart: empty render", async function (assert) {
        assert.expect(2);

        var form = await createView({
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
                    return Promise.resolve({
                        children: [],
                        managers: [],
                        managers_more: false,
                    });
                } else if (route === '/hr/get_redirect_model') {
                  return Promise.resolve('hr.employee');
                }
                return this._super(route, args);
            }
        });
        assert.strictEqual(form.$('[name="child_ids"]').children().length, 1,
            "the chart should have 1 child");
        form.destroy();
    });
    QUnit.test("hr org chart: render without data", async function (assert) {
        assert.expect(2);

        var form = await createView({
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
                    return Promise.resolve({}); // return no data
                }
                return this._super(route, args);
            }
        });
        assert.strictEqual(form.$('[name="child_ids"]').children().length, 1,
            "the chart should have 1 child");
        form.destroy();
    });
    QUnit.test("hr org chart: basic render", async function (assert) {
        assert.expect(3);

        var form = await createView({
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
                    return Promise.resolve({
                        children: [{
                            direct_sub_count: 0,
                            indirect_sub_count: 0,
                            job_id: 2,
                            job_name: 'Sub-Gooroo',
                            link: 'fake_link',
                            name: 'Michael Hawkins',
                            id: 2,
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
                } else if (route === '/hr/get_redirect_model') {
                  return Promise.resolve('hr.employee');
                }
                return this._super(route, args);
            }
        });
        assert.containsOnce(form, '.o_org_chart_entry_sub',
            "the chart should have 1 subordinate");
        assert.containsOnce(form, '.o_org_chart_entry_self',
            "the current employee should only be displayed once in the chart");
        form.destroy();
    });
    QUnit.test("hr org chart: basic manager render", async function (assert) {
        assert.expect(4);

        var form = await createView({
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
                    return Promise.resolve({
                        children: [{
                            direct_sub_count: 0,
                            indirect_sub_count: 0,
                            job_id: 2,
                            job_name: 'Sub-Gooroo',
                            link: 'fake_link',
                            name: 'Michael Hawkins',
                            id: 2,
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
                } else if (route === '/hr/get_redirect_model') {
                  return Promise.resolve('hr.employee');
                }
                return this._super(route, args);
            }
        });
        assert.containsOnce(form, '.o_org_chart_group_up .o_org_chart_entry_manager', "the chart should have 1 manager");
        assert.containsOnce(form, '.o_org_chart_group_down .o_org_chart_entry_sub', "the chart should have 1 subordinate");
        assert.containsOnce(form, '.o_org_chart_entry_self', "the chart should have only once the current employee");
        form.destroy();
    });
});

});
