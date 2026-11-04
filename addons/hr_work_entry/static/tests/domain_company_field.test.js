import { beforeEach, expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    selectFieldDropdownItem,
    serverState,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import "@hr_work_entry/components/domain_company_field/domain_company_field";

const FORM_ARCH = `
    <form>
        <field name="company_id"/>
        <field name="employee_domain" widget="domain_company" options="{'model': 'hr.employee'}"/>
    </form>`;

class HrEmployee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();
    company_id = fields.Many2one({ relation: "res.company" });

    _records = [
        { id: 1, name: "Alice", company_id: 1 },
        { id: 2, name: "Carol", company_id: 1 },
        { id: 3, name: "Bob", company_id: 2 },
    ];

    _views = {
        list: `<list><field name="name"/></list>`,
        search: `<search><field name="name"/></search>`,
    };
}

class HrTimeRule extends models.Model {
    _name = "hr.time.rule";

    name = fields.Char();
    company_id = fields.Many2one({ relation: "res.company" });
    employee_domain = fields.Char();

    _records = [
        { id: 1, name: "Rule 1", company_id: 1, employee_domain: "[]" },
        { id: 2, name: "Rule 2", company_id: false, employee_domain: "[]" },
    ];
}

defineMailModels();
defineModels([HrEmployee, HrTimeRule]);

beforeEach(() => {
    serverState.companies = [
        { id: 1, name: "Company 1" },
        { id: 2, name: "Company 2" },
    ];
});

test.tags("desktop");
test("domain_company widget filters employees by company_id", async () => {
    await mountView({ type: "form", resModel: "hr.time.rule", resId: 1, arch: FORM_ARCH });
    expect(".o_domain_show_selection_button").toHaveText("2 record(s)");
    await contains(".o_domain_show_selection_button").click();
    expect(".modal .o_data_row").toHaveCount(2);
    expect(".modal .o_data_row:eq(0) .o_data_cell[name='name']").toHaveText("Alice");
    expect(".modal .o_data_row:eq(1) .o_data_cell[name='name']").toHaveText("Carol");
});

test.tags("desktop");
test("domain_company widget updates when company_id changes", async () => {
    await mountView({ type: "form", resModel: "hr.time.rule", resId: 1, arch: FORM_ARCH });
    await selectFieldDropdownItem("company_id", "Company 2");
    expect(".o_domain_show_selection_button").toHaveText("1 record(s)");
    await contains(".o_domain_show_selection_button").click();
    expect(".modal .o_data_row").toHaveCount(1);
    expect(".modal .o_data_row .o_data_cell[name='name']").toHaveText("Bob");
});

test.tags("desktop");
test("domain_company widget shows all employees without company_id", async () => {
    await mountView({ type: "form", resModel: "hr.time.rule", resId: 2, arch: FORM_ARCH });
    expect(".o_domain_show_selection_button").toHaveText("3 record(s)");
    await contains(".o_domain_show_selection_button").click();
    expect(".modal .o_data_row").toHaveCount(3);
});
