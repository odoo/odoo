import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class Employee extends models.Model {
    _name = "hr.employee";

    child_ids = fields.One2many({
        string: "Subordinates",
        relation: "hr.employee",
        relation_field: "parent_id",
    });

    _records = [
        {
            id: 1,
            child_ids: [],
        },
    ];
}

defineModels([Employee]);
defineMailModels();

test("hr org chart: empty render", async () => {
    expect.assertions(2);

    onRpc("/hr/get_org_chart", async (request) => {
        const { params: args } = await request.json();
        expect("employee_id" in args).toBe(true, {
            message: "it should have 'employee_id' as argument",
        });
        return {
            children: [],
            managers: [],
            managers_more: false,
        };
    });
    onRpc("/hr/get_redirect_model", () => {
        return "hr.employee";
    });
    await mountView({
        type: "form",
        resModel: "hr.employee",
        arch: `<form><field name="child_ids" widget="hr_org_chart"/></form>`,
        resId: 1,
    });
    expect(queryOne('[name="child_ids"]').children).toHaveLength(1, {
        message: "the chart should have 1 child",
    });
});
test("hr org chart: render without data", async () => {
    expect.assertions(2);

    onRpc("/hr/get_org_chart", async (request) => {
        const { params: args } = await request.json();
        expect("employee_id" in args).toBe(true, {
            message: "it should have 'employee_id' as argument",
        });
        return {}; // return no data
    });
    await mountView({
        type: "form",
        resModel: "hr.employee",
        arch: `<form><field name="child_ids" widget="hr_org_chart"/></form>`,
        resId: 1,
    });
    expect(queryOne('[name="child_ids"]').children).toHaveLength(1, {
        message: "the chart should have 1 child",
    });
});
test("hr org chart: basic render", async () => {
    expect.assertions(3);

    onRpc("/hr/get_org_chart", async (request) => {
        const { params: args } = await request.json();
        expect("employee_id" in args).toBe(true, {
            message: "it should have 'employee_id' as argument",
        });
        return {
            children: [
                {
                    direct_sub_count: 0,
                    indirect_sub_count: 0,
                    job_id: 2,
                    job_name: "Sub-Gooroo",
                    link: "fake_link",
                    name: "Michael Hawkins",
                    id: 2,
                },
            ],
            managers: [],
            managers_more: false,
            self: {
                direct_sub_count: 1,
                id: 1,
                indirect_sub_count: 1,
                job_id: 1,
                job_name: "Gooroo",
                link: "fake_link",
                name: "Antoine Langlais",
            },
        };
    });
    onRpc("/hr/get_redirect_model", () => {
        return "hr.employee";
    });
    await mountView({
        type: "form",
        resModel: "hr.employee",
        arch: `<form>
                <sheet>
                    <div id="o_employee_container">
                        <div id="o_employee_main">
                            <div id="o_employee_right">
                                <field name="child_ids" widget="hr_org_chart"/>
                            </div>
                        </div>
                    </div>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect(".o_org_chart_entry_sub").toHaveCount(1, {
        message: "the chart should have 1 subordinate",
    });
    expect(".o_org_chart_entry_self").toHaveCount(1, {
        message: "the current employee should only be displayed once in the chart",
    });
});
test("hr org chart: basic manager render", async () => {
    expect.assertions(4);

    onRpc("/hr/get_org_chart", async (request) => {
        const { params: args } = await request.json();
        expect("employee_id" in args).toBe(true, {
            message: "it should have 'employee_id' as argument",
        });
        return {
            children: [
                {
                    direct_sub_count: 0,
                    indirect_sub_count: 0,
                    job_id: 2,
                    job_name: "Sub-Gooroo",
                    link: "fake_link",
                    name: "Michael Hawkins",
                    id: 2,
                },
            ],
            managers: [
                {
                    direct_sub_count: 1,
                    id: 1,
                    indirect_sub_count: 2,
                    job_id: 1,
                    job_name: "Chief Gooroo",
                    link: "fake_link",
                    name: "Antoine Langlais",
                },
            ],
            managers_more: false,
            self: {
                direct_sub_count: 1,
                id: 1,
                indirect_sub_count: 1,
                job_id: 3,
                job_name: "Gooroo",
                link: "fake_link",
                name: "John Smith",
            },
        };
    });
    onRpc("/hr/get_redirect_model", () => {
        return "hr.employee";
    });
    await mountView({
        type: "form",
        resModel: "hr.employee",
        arch: `<form>
                <sheet>
                    <div id="o_employee_container">
                        <div id="o_employee_main">
                            <div id="o_employee_right">
                                <field name="child_ids" widget="hr_org_chart"/>
                            </div>
                        </div>
                    </div>
                </sheet>
            </form>`,
        resId: 1,
    });
    expect(".o_org_chart_group_up .o_org_chart_entry_manager").toHaveCount(1, {
        message: "the chart should have 1 manager",
    });
    expect(".o_org_chart_group_down .o_org_chart_entry_sub").toHaveCount(1, {
        message: "the chart should have 1 subordinate",
    });
    expect(".o_org_chart_entry_self").toHaveCount(1, {
        message: "the chart should have only once the current employee",
    });
});
