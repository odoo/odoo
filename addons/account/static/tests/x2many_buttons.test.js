import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test } from "@odoo/hoot";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class AccountMove extends models.Model {
    _name = "account.move";

    name = fields.Char();
    duplicated_ref_ids = fields.Many2many({
        string: "Duplicated Bills",
        relation: "account.move",
    });
    ref = fields.Char({ string: "Bill Reference" });

    _records = [
        // for the sake of mocking data, we don't care about the consistency of duplicated refs across records
        { id: 1, display_name: "Bill 1", duplicated_ref_ids: [2, 3], ref: "b1" },
        { id: 2, display_name: "Bill 2", duplicated_ref_ids: [1], ref: "b2" },
        { id: 3, display_name: "Bill 3", duplicated_ref_ids: [1], ref: "b3" },
        { id: 4, display_name: "Bill 4", duplicated_ref_ids: [1, 2, 3], ref: "b4" },
        { id: 5, display_name: "Bill 5", duplicated_ref_ids: [], ref: "b5" },
        { id: 6, display_name: "Bill 6", duplicated_ref_ids: [1, 2, 3, 4, 5], ref: "b6" },
    ];

    _views = {
        form: `
            <form>
                <field name="display_name"/>
                <field name="ref"/>
                <field name="duplicated_ref_ids" widget="x2many_buttons"/>
            </form>
        `,
    };
}

defineModels([AccountMove]);
defineMailModels();

test("component rendering: less than 3 records on field", async () => {
    expect.assertions(2);

    await mountView({
        resModel: "account.move",
        resId: 1,
        type: "form",
    });
    expect(".o_field_x2many_buttons").toHaveCount(1);
    expect(".o_field_x2many_buttons button").toHaveCount(2);
});

test("component rendering: exactly 3 records on field", async () => {
    expect.assertions(2);

    await mountView({
        resModel: "account.move",
        resId: 4,
        type: "form",
    });
    expect(".o_field_x2many_buttons").toHaveCount(1);
    expect(".o_field_x2many_buttons button").toHaveCount(3);
});

test("component rendering: more than 3 records on field", async () => {
    expect.assertions(3);

    await mountView({
        resModel: "account.move",
        resId: 6,
        type: "form",
    });
    expect(".o_field_x2many_buttons").toHaveCount(1);
    expect(".o_field_x2many_buttons button").toHaveCount(4);
    expect(".o_field_x2many_buttons button:eq(3)").toHaveText("... (View all)");
});

test("edit record and check if edits get discarded when click on one of the buttons and redirects to proper record", async () => {
    onRpc("account.move", "action_open_business_doc", ({ args }) => {
        expect.step("action_open_business_doc");
        expect(args.length).toBe(1);
        expect(args[0]).toBe(2);
        return {
            res_model: "account.move",
            res_id: 2,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        };
    });
    await mountView({
        resModel: "account.move",
        resId: 1,
        type: "form",
    });

    await contains("[name='ref'] input").edit("new ref");
    expect("[name='ref'] input").toHaveValue("new ref");
    await contains(".o_field_x2many_buttons button").click();
    expect("[name='ref'] input").toHaveValue("b1");
    expect.verifySteps(["action_open_business_doc"]);
});

// test if clicking on last button redirects to records in list view
test("redirect to list view and discards edits when clicking on last button with more than 3 records on field", async () => {
    expect.assertions(3);
    mockService("action", {
        doAction(action) {
            expect(action).toEqual({
                domain: [["id", "in", [1, 2, 3, 4, 5]]],
                name: "Duplicated Bills",
                res_model: "account.move",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                context: {
                    list_view_ref: "account.view_duplicated_moves_tree_js",
                },
            });
        },
    });
    await mountView({
        resModel: "account.move",
        resId: 6,
        type: "form",
    });
    await contains("[name='ref'] input").edit("new ref");
    expect("[name='ref'] input").toHaveValue("new ref");
    await contains(".o_field_x2many_buttons button:eq(3)").click();
    expect("[name='ref'] input").toHaveValue("b6");
});
