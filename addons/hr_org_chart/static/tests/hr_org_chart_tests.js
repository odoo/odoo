/** @odoo-module **/

import { getFixture, click, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let target;
let serverData;

QUnit.module("hr_org_chart", {
    async beforeEach() {
        target = getFixture();
        serverData = {
            models: {
                hr_employee: {
                    fields: {
                        child_ids: {string: "one2many Subordinates field", type: "one2many", relation: 'hr_employee'},
                    },
                    records: [{
                        id: 1,
                        child_ids: [],
                    }]
                },
            },
        };
        setupViewRegistries();
    },
}, function () {
    QUnit.test("hr org chart: empty render", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: 'hr_employee',
            serverData: serverData,
            arch:
                '<form>' +
                    '<field name="child_ids" widget="hr_org_chart"/>' +
                '</form>',
            resId: 1,
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
            }
        });
        assert.strictEqual($(target.querySelector('[name="child_ids"]')).children().length, 1,
            "the chart should have 1 child");
    });
    QUnit.test("hr org chart: render without data", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "form",
            resModel: 'hr_employee',
            serverData: serverData,
            arch:
                '<form>' +
                    '<field name="child_ids" widget="hr_org_chart"/>' +
                '</form>',
            resId: 1,
            mockRPC: function (route, args) {
                if (route === '/hr/get_org_chart') {
                    assert.ok('employee_id' in args, "it should have 'employee_id' as argument");
                    return Promise.resolve({}); // return no data
                }
            }
        });
        assert.strictEqual($(target.querySelector('[name="child_ids"]')).children().length, 1,
            "the chart should have 1 child");
    });
    QUnit.test("hr org chart: basic render", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: 'hr_employee',
            serverData: serverData,
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
            resId: 1,
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
            }
        });
        assert.containsOnce(target, '.o_org_chart_entry_sub',
            "the chart should have 1 subordinate");
        assert.containsOnce(target, '.o_org_chart_entry_self',
            "the current employee should only be displayed once in the chart");
    });
    QUnit.test("hr org chart: basic manager render", async function (assert) {
        assert.expect(4);

        await makeView({
            type: "form",
            resModel: 'hr_employee',
            serverData: serverData,
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
            resId: 1,
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
            }
        });
        assert.containsOnce(target, '.o_org_chart_group_up .o_org_chart_entry_manager', "the chart should have 1 manager");
        assert.containsOnce(target, '.o_org_chart_group_down .o_org_chart_entry_sub', "the chart should have 1 subordinate");
        assert.containsOnce(target, '.o_org_chart_entry_self', "the chart should have only once the current employee");
    });
    QUnit.test("hr org chart: scroll in chart", async function (assert) {
        assert.expect(15);

        await makeView({
            type: "form",
            resModel: 'hr_employee',
            serverData: serverData,
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
            resId: 1,
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
                        },
                        {
                            direct_sub_count: 0,
                            indirect_sub_count: 0,
                            job_id: 14,
                            job_name: 'CTO',
                            link: 'cto_link',
                            name: 'Henry Ford',
                            id: 14,
                        }
                    ],
                        managers: [
                            {
                                direct_sub_count: 1,
                                indirect_sub_count: 9,
                                job_id: 7,
                                job_name: 'Project Manager',
                                link: 'project_manager_link',
                                name: 'Alice Smith',
                                id: 7,
                            },
                            {
                                direct_sub_count: 1,
                                indirect_sub_count: 8,
                                job_id: 8,
                                job_name: 'Team Lead',
                                link: 'team_lead_link',
                                name: 'Bob Johnson',
                                id: 8,
                            },
                            {
                                direct_sub_count: 1,
                                indirect_sub_count: 7,
                                job_id: 9,
                                job_name: 'Senior Engineer',
                                link: 'senior_engineer_link',
                                name: 'Charlie Brown',
                                id: 9,
                            },
                            {
                                direct_sub_count: 1,
                                indirect_sub_count: 6,
                                job_id: 10,
                                job_name: 'Junior Engineer',
                                link: 'junior_engineer_link',
                                name: 'Diana Prince',
                                id: 10,
                            },
                            {
                                direct_sub_count: 1,
                                indirect_sub_count: 5,
                                job_id: 11,
                                job_name: 'Intern',
                                link: 'intern_link',
                                name: 'Eve Adams',
                                id: 11,
                            },
                            {
                                direct_sub_count: 1,
                                indirect_sub_count: 4,
                                job_id: 12,
                                job_name: 'Director',
                                link: 'director_link',
                                name: 'Frank White',
                                id: 12,
                            },
                            {
                                direct_sub_count: 1,
                                indirect_sub_count: 3,
                                job_id: 13,
                                job_name: 'CEO',
                                link: 'ceo_link',
                                name: 'Grace Hopper',
                                id: 13,
                            }
                        ],
                        managers_more: true,
                        self: {
                            direct_sub_count: 2,
                            id: 1,
                            indirect_sub_count: 2,
                            job_id: 1,
                            job_name: 'Gooroo',
                            link: 'fake_link',
                            name: 'Antoine Langlais',
                        },
                        excess_managers_count: 2,
                    });
                } else if (route === '/hr/get_redirect_model') {
                  return Promise.resolve('hr.employee');
                }
            }
        });
        const entries = $(target.querySelectorAll('.o_org_chart_entry'));
        const scrollUpButton = $(target.querySelector('.o_org_chart_scroll_up>a'));
        const scrollDownButton = $(target.querySelector('.o_org_chart_scroll_down>a'));
        const entriesWrapper = $(target.querySelector('.o_org_chart_group_wrapper'));
        // the count of all displayed employees in the chart should be 10
        assert.strictEqual(entries.length, 10,
            "the chart should have 10 child");
        await waitToScroll();
        // check that that the first two managers are not displayed yet in the chart
        assert.strictEqual(isElementOverflowingParent(entries[0], entriesWrapper[0]), true,
            "the first manager should be displayed the chart");
        assert.strictEqual(isElementOverflowingParent(entries[1], entriesWrapper[0]), true,
            "the second manager should be displayed the chart");
        // assert the scroll up button is in the dom
        assert.strictEqual(scrollUpButton.length, 1,
            "the scroll up button should be in the dom");
        // assert the scroll down button is in the dom
        assert.strictEqual(scrollDownButton.length, 1,
            "the scroll down button should be in the dom");
        // scroll up twice
        await click(scrollUpButton[0]);
        await click(scrollUpButton[0]);
        await waitToScroll();
        // assert that the first two managers are now displayed in the chart
        assert.strictEqual(isElementOverflowingParent(entries[0], entriesWrapper[0]), false,
            "the first manager should not be displayed the chart");
        assert.strictEqual(isElementOverflowingParent(entries[1], entriesWrapper[0]), false,
            "the second manager should not be displayed the chart");
        // assert the scroll up button is hidden the dom
        assert.strictEqual(target.querySelector(".o_org_chart_scroll_up").style.visibility, "hidden",
            "the scroll up button should be hidden");
        // scroll down three times
        await click(scrollDownButton[0]);
        await click(scrollDownButton[0]);
        await click(scrollDownButton[0]);
        await waitToScroll();
        // assert that the first three managers are now not displayed in the chart
        assert.strictEqual(isElementOverflowingParent(entries[0], entriesWrapper[0]), true,
            "the first manager should be displayed the chart");
        assert.strictEqual(isElementOverflowingParent(entries[1], entriesWrapper[0]), true,
            "the second manager should be displayed the chart");
        assert.strictEqual(isElementOverflowingParent(entries[2], entriesWrapper[0]), true,
            "the third manager should be displayed the chart");
        // assert that the two subordinates are displayed in the chart
        assert.strictEqual(isElementOverflowingParent(entries[8], entriesWrapper[0]), false,
            "the first subordinate should not be displayed the chart");
        assert.strictEqual(isElementOverflowingParent(entries[9], entriesWrapper[0]), false,
            "the second subordinate should not be displayed the chart");
        // assert the scroll down button is hidden the dom
        assert.strictEqual(target.querySelector(".o_org_chart_scroll_down").style.visibility, "hidden",
            "the scroll down button should be hidden");
    });
});

async function waitToScroll(count = 12){
    for (let i = 0; i < count; i++){
        await nextTick();
    }
}

function isElementOverflowingParent(child, parent) {
    const childRect = child.getBoundingClientRect();
    const parentRect = parent.getBoundingClientRect();

    return (
      childRect.top < parentRect.top ||
      childRect.top > parentRect.bottom
    );
  }
