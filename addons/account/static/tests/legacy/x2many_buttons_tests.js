/** @odoo-module **/
import { click, editInput, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";


QUnit.module("Fields", (hooks) => {
    const serverData = {
        models: {
            "account.move": {
                fields: {
                    display_name: {
                        "string": "Display Name",
                        "type": "string"
                    },
                    duplicated_ref_ids: {
                        "string": "Duplicated Bills",
                        "type": "many2many",
                        "relation": "account.move"
                    },
                    ref: {
                        "string": "Bill Reference",
                        "type": "char"
                    }
                },
                records: [
                    // for the sake of mocking data, we don't care about the consistency of duplicated refs across records
                    { id: 1, display_name: "Bill 1", duplicated_ref_ids: [2, 3] , ref: "b1" },
                    { id: 2, display_name: "Bill 2", duplicated_ref_ids: [1] , ref: "b2" },
                    { id: 3, display_name: "Bill 3", duplicated_ref_ids: [1] , ref: "b3" },
                    { id: 4, display_name: "Bill 4", duplicated_ref_ids: [1, 2, 3] , ref: "b4" },
                    { id: 5, display_name: "Bill 5", duplicated_ref_ids: [] , ref: "b5"},
                    { id: 6, display_name: "Bill 6", duplicated_ref_ids: [1, 2, 3, 4, 5] , ref: "b6" },
                ],
            }
        }
    };
    let target;
    const fromArch = `
        <form>
            <field name="display_name"/>
            <field name="ref"/>
            <field name="duplicated_ref_ids" widget="x2many_buttons"/>
        </form>
    `;

    hooks.beforeEach(() => {
        target = getFixture();

        setupViewRegistries();
    });

    QUnit.module("X2ManyButtonsField");

    QUnit.test("component rendering: less than 3 records on field", async function (assert) {
        assert.expect(2);

        await makeView({
            resModel: "account.move",
            resId: 1,
            serverData,
            arch: fromArch,
            type: "form",
        });
        assert.containsOnce(target, ".o_field_x2many_buttons", "should have rendered a x2many_buttons field");
        assert.strictEqual(target.querySelectorAll(".o_field_x2many_buttons button").length, 2, "buttons should be rendered");
    });

    QUnit.test("component rendering: exactly 3 records on field", async function (assert) {
        assert.expect(2);

        await makeView({
            resModel: "account.move",
            resId: 4,
            serverData,
            arch: fromArch,
            type: "form",
        });
        assert.containsOnce(target, ".o_field_x2many_buttons", "should have rendered a x2many_buttons field");
        assert.strictEqual(target.querySelectorAll(".o_field_x2many_buttons button").length, 3, "buttons should be rendered");
    });

    QUnit.test("component rendering: more than 3 records on field", async function (assert) {
        assert.expect(3);

        await makeView({
            resModel: "account.move",
            resId: 6,
            serverData,
            arch: fromArch,
            type: "form",
        });
        assert.containsOnce(target, ".o_field_x2many_buttons", "should have rendered a x2many_buttons field");
        const buttons = target.querySelectorAll(".o_field_x2many_buttons button");
        assert.strictEqual(buttons.length, 4, "buttons should be rendered");
        assert.strictEqual(buttons[3].innerText, "... (View all)", "The 4th button should be the view all one");
    });

    QUnit.test("edit record and check if edits get discarded when click on one of the buttons and redirects to proper record", async function (assert) {
        assert.expect(8);
        const modelAction = {
            res_model: "account.move",
            res_id: 2,
            type: "ir.actions.act_window",
            views: [[false, "form"]],
        }

        await makeView({
            resModel: "account.move",
            resId: 1,
            serverData,
            arch: fromArch,
            type: "form",
            // as the redirection to the relevant model happens through py action, for mocking purposes we assume a simple account.move to account.move scenario
            mockRPC(route, { args, method, model }) {
                if (route === "/web/dataset/call_kw/account.move/action_open_business_doc") {
                    assert.step("action_open_business_doc");
                    assert.strictEqual(
                        model,
                        "account.move",
                        'The model should be "account.move"'
                    );
                    assert.strictEqual(method, "action_open_business_doc");
                    assert.strictEqual(
                        args.length,
                        1,
                        "There should be one record"
                    );
                    assert.strictEqual(args[0], 2, "The record id returned should be 2");
                    return modelAction;
                }
            }
        });

        await editInput(target, "[name='ref'] input", "new ref");
        assert.strictEqual(target.querySelector("[name='ref'] input").value, "new ref", "should have edited the input");
        await click(target.querySelector(".o_field_x2many_buttons button"));
        assert.strictEqual(target.querySelector("[name='ref'] input").value, "b1", "should have discarded the input");
        assert.verifySteps(["action_open_business_doc"])
    });

    // test if clicking on last button redirects to records in list view
    QUnit.test("redirect to list view and discards edits when clicking on last button with more than 3 records on field", async function (assert) {
        assert.expect(3);
        const form = await makeView({
            resModel: "account.move",
            resId: 6,
            serverData,
            arch: fromArch,
            type: "form",
        });
        patchWithCleanup(form.env.services.action, {
            doAction(action) {
                assert.deepEqual(action, {
                    domain: [["id", "in", [1,2,3,4,5]]],
                    name: "Duplicated Bills",
                    res_model: "account.move",
                    type: "ir.actions.act_window",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                    context: {
                        form_view_ref: "account.view_duplicated_moves_tree_js",
                    }
                });
            }
        });
        const x2mbuttons = target.querySelector(".o_field_x2many_buttons");
        await editInput(target, "[name='ref'] input", "new ref");
        assert.strictEqual(target.querySelector("[name='ref'] input").value, "new ref", "should have edited the input");
        await click(x2mbuttons.querySelectorAll("button")[3]);
        assert.strictEqual(target.querySelector("[name='ref'] input").value, "b6", "should have discarded the input");
    });
});
