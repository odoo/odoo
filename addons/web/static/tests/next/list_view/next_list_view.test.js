import { expect, queryAllTexts, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    getPagerLimit,
    getPagerValue,
    models,
    mountView,
    pagerNext,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    name = fields.Char();
    email = fields.Char();
    parent_id = fields.Many2one({ relation: "partner" });
    state = fields.Selection({
        selection: [
            ["draft", "Draft"],
            ["done", "Done"],
        ],
    });

    _records = [
        { id: 1, name: "first record", email: "first@example.com", state: "draft" },
        { id: 2, name: "second record", parent_id: 1, state: "done" },
        { id: 3, name: "third record" },
    ];
}

defineModels([Partner]);

const arch = `
    <list js_class="next_list">
        <field name="name"/>
        <field name="email" optional="hide"/>
        <field name="display_name" column_invisible="True"/>
        <field name="parent_id" string="Parent"/>
        <field name="state"/>
    </list>`;

test("next_list displays the records", async () => {
    await mountView({ resModel: "partner", type: "list", arch });
    expect(queryAllTexts("thead th")).toEqual(["Name", "Parent", "State"]);
    expect(queryAllTexts(".o_data_row:eq(0) .o_data_cell")).toEqual(["first record", "", "Draft"]);
    expect(queryAllTexts(".o_data_row:eq(1) .o_data_cell")).toEqual([
        "second record",
        "first record",
        "Done",
    ]);
    expect(".o_data_row").toHaveCount(3);
});

test("next_list opens a record in the form view", async () => {
    await mountView({
        resModel: "partner",
        type: "list",
        arch,
        selectRecord(resId, { activeIds }) {
            expect.step([resId, activeIds]);
        },
    });
    await contains(".o_data_row:eq(1) .o_data_cell").click();
    expect.verifySteps([[2, [1, 2, 3]]]);
});

test("next_list creates a record in the form view", async () => {
    await mountView({
        resModel: "partner",
        type: "list",
        arch,
        createRecord() {
            expect.step("createRecord");
        },
    });
    await contains(".o_list_button_add").click();
    expect.verifySteps(["createRecord"]);
});

test("next_list loads the records page by page", async () => {
    await mountView({
        resModel: "partner",
        type: "list",
        arch: `<list js_class="next_list" limit="2"><field name="name"/></list>`,
    });
    expect(queryAllTexts(".o_data_cell")).toEqual(["first record", "second record"]);
    expect(getPagerValue()).toEqual([1, 2]);
    expect(getPagerLimit()).toBe(3);

    await pagerNext();
    expect(queryAllTexts(".o_data_cell")).toEqual(["third record"]);
    expect(getPagerValue()).toEqual([3, 3]);
});
