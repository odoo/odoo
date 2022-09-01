/** @odoo-module **/

import { registry } from "@web/core/registry";
import { commandService } from "@web/core/commands/command_service";
import {
    click,
    getFixture,
    nextTick,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

const serviceRegistry = registry.category("services");

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        foo: {
                            string: "Foo",
                            type: "char",
                        },
                        sequence: { type: "integer", string: "Sequence", searchable: true },
                        selection: {
                            string: "Selection",
                            type: "selection",
                            selection: [
                                ["normal", "Normal"],
                                ["blocked", "Blocked"],
                                ["done", "Done"],
                            ],
                        },
                    },
                    records: [
                        {
                            id: 1,
                            foo: "yop",
                            selection: "blocked",
                        },
                        {
                            id: 2,
                            foo: "blip",
                            selection: "normal",
                        },
                        {
                            id: 4,
                            foo: "abc",
                            selection: "done",
                        },
                        { id: 3, foo: "gnap" },
                        { id: 5, foo: "blop" },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("PriorityField");

    QUnit.test("PriorityField when not set", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="selection" widget="priority" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.containsOnce(
            target,
            ".o_field_widget .o_priority:not(.o_field_empty)",
            "widget should be considered set, even though there is no value for this field"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should have no full star since there is no value"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            2,
            "should have two empty stars since there is no value"
        );
    });

    QUnit.test("PriorityField tooltip", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="selection" widget="priority"/>
                        </group>
                    </sheet>
                </form>`,
            resId: 1,
        });

        // check data-tooltip attribute (used by the tooltip service)
        const stars = target.querySelectorAll(".o_field_widget .o_priority a.o_priority_star");
        assert.strictEqual(
            stars[0].dataset["tooltip"],
            "Selection: Blocked",
            "Should set field label and correct selection label as title attribute (tooltip)"
        );
        assert.strictEqual(
            stars[1].dataset["tooltip"],
            "Selection: Done",
            "Should set field label and correct selection label as title attribute (tooltip)"
        );
    });

    QUnit.test("PriorityField in form view", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="selection" widget="priority" />
                        </group>
                    </sheet>
                </form>`,
        });

        assert.containsOnce(
            target,
            ".o_field_widget .o_priority:not(.o_field_empty)",
            "widget should be considered set"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should have one full star since the value is the second value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should have one empty star since the value is the second value"
        );

        // hover last star
        let stars = target.querySelectorAll(
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o"
        );
        await triggerEvent(stars[stars.length - 1], null, "mouseenter");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            2,
            "should temporary have two full stars since we are hovering the third value"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should temporary have no empty star since we are hovering the third value"
        );

        await triggerEvent(stars[stars.length - 1], null, "mouseleave");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should temporary have two full stars since we are hovering the third value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should temporary have no empty star since we are hovering the third value"
        );

        // switch to edit mode and check the result
        await click(target, ".o_form_button_edit");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should still have one full star since the value is the second value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should still have one empty star since the value is the second value"
        );

        // save
        await click(target, ".o_form_button_save");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should still have one full star since the value is the second value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should still have one empty star since the value is the second value"
        );

        // switch to edit mode to check that the new value was properly written
        await click(target, ".o_form_button_edit");

        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should still have one full star since the value is the second value"
        );
        assert.containsOnce(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should still have one empty star since the value is the second value"
        );

        // click on the second star in edit mode
        stars = target.querySelectorAll(".o_field_widget .o_priority a.o_priority_star.fa-star-o");
        await click(stars[stars.length - 1]);

        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should now have no empty star since the value is the third value"
        );

        // save
        await click(target, ".o_form_button_save");
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsN(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star-o",
            "should now have no empty star since the value is the third value"
        );
    });

    QUnit.test("PriorityField can write after adding a record -- kanban", async function (assert) {
        serverData.models.partner.fields.selection.selection = [
            ["0", 0],
            ["1", 1],
        ];
        serverData.models.partner.records[0].selection = "0";

        serverData.views = {
            "partner,myquickview,form": `<form><field name="display_name" /></form>`,
        };
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            domain: [["id", "=", 1]],
            groupBy: ["foo"],
            arch: `
                <kanban on_create="quick_create" quick_create_view="myquickview">
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_card oe_kanban_global_click">
                                <field name="selection" widget="priority"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            mockRPC(route, args) {
                if (args.method === "write") {
                    assert.step(`write ${JSON.stringify(args.args)}`);
                }
            },
        });
        assert.containsNone(target, ".o_kanban_record .fa-star");
        await click(target.querySelector(".o_priority a.o_priority_star.fa-star-o"), null, true);
        assert.verifySteps(['write [[1],{"selection":"1"}]']);
        assert.containsOnce(target, ".o_kanban_record .fa-star");

        await click(target, ".o-kanban-button-new");
        await click(target, ".o_kanban_quick_create .o_kanban_add");
        await click(target.querySelector(".o_priority a.o_priority_star.fa-star-o"), null, true);
        assert.verifySteps(['write [[6],{"selection":"1"}]']);
        assert.containsN(target, ".o_kanban_record .fa-star", 2);
    });

    QUnit.test("PriorityField in editable list view", async function (assert) {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="selection" widget="priority" />
                </tree>`,
        });

        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority:not(.o_field_empty)",
            "widget should be considered set"
        );
        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should have one full star since the value is the second value"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            "should have one empty star since the value is the second value"
        );

        // switch to edit mode and check the result
        await click(target.querySelector("tbody td:not(.o_list_record_selector)"));

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should have one full star since the value is the second value"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            "should have one empty star since the value is the second value"
        );

        // save
        await click(target, ".o_list_button_save");

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should have one full star since the value is the second value"
        );
        assert.containsOnce(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            "should have one empty star since the value is the second value"
        );

        // hover last star
        await triggerEvent(
            target.querySelector(".o_data_row"),
            ".o_priority a.o_priority_star.fa-star-o",
            "mouseenter"
        );

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should have two stars for representing each possible value: no star, one star and two stars"
        );
        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            "a.o_priority_star.fa-star",
            2,
            "should temporary have two full stars since we are hovering the third value"
        );
        assert.containsNone(
            target.querySelectorAll(".o_data_row")[0],
            "a.o_priority_star.fa-star-o",
            "should temporary have no empty star since we are hovering the third value"
        );

        // click on the first star in readonly mode
        await click(target.querySelector(".o_priority a.o_priority_star.fa-star"));

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsNone(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should now have no full star since the value is the first value"
        );
        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            2,
            "should now have two empty stars since the value is the first value"
        );

        // re-enter edit mode to force re-rendering the widget to check if the value was correctly saved
        await click(target.querySelector("tbody td:not(.o_list_record_selector)"));

        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsNone(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star",
            "should now only have no full star since the value is the first value"
        );
        assert.containsN(
            target.querySelectorAll(".o_data_row")[0],
            ".o_priority a.o_priority_star.fa-star-o",
            2,
            "should now have two empty stars since the value is the first value"
        );

        // Click on second star in edit mode
        const stars = target.querySelectorAll(".o_priority a.o_priority_star.fa-star-o");
        await click(stars[stars.length - 1]);

        let rows = target.querySelectorAll(".o_data_row");
        assert.containsN(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsN(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star.fa-star",
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.containsNone(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star.fa-star-o",
            "should now have no empty star since the value is the third value"
        );

        // save
        await click(target, ".o_list_button_save");
        rows = target.querySelectorAll(".o_data_row");

        assert.containsN(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star",
            2,
            "should still have two stars"
        );
        assert.containsN(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star.fa-star",
            2,
            "should now have two full stars since the value is the third value"
        );
        assert.containsNone(
            rows[rows.length - 1],
            ".o_priority a.o_priority_star.fa-star-o",
            "should now have no empty star since the value is the third value"
        );
    });

    QUnit.test("PriorityField with readonly attribute", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: '<form><field name="selection" widget="priority" readonly="1"/></form>',
            mockRPC(route, args) {
                if (args.method === "write") {
                    throw new Error("should not save");
                }
            },
        });

        assert.containsN(
            target,
            "span.o_priority_star.fa.fa-star-o",
            2,
            "stars of priority widget should rendered with span tag if readonly"
        );

        await triggerEvent(
            target.querySelectorAll(".o_priority_star.fa-star-o")[1],
            null,
            "mouseenter"
        );
        assert.containsNone(
            target,
            ".o_field_widget .o_priority a.o_priority_star.fa-star",
            "should have no full stars on hover since the field is readonly"
        );

        await click(target.querySelectorAll(".o_priority_star.fa-star-o")[1]);
        assert.containsN(
            target,
            "span.o_priority_star.fa.fa-star-o",
            2,
            "should still have two stars"
        );
    });

    QUnit.test(
        'PriorityField edited by the smart action "Set priority..."',
        async function (assert) {
            serviceRegistry.add("command", commandService);

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="selection" widget="priority"/>
                    </form>`,
                resId: 1,
            });

            assert.containsOnce(target, "a.fa-star");

            triggerHotkey("control+k");
            await nextTick();
            const idx = [...target.querySelectorAll(".o_command")]
                .map((el) => el.textContent)
                .indexOf("Set priority...ALT + R");
            assert.ok(idx >= 0);

            await click([...target.querySelectorAll(".o_command")][idx]);
            await nextTick();
            assert.deepEqual(
                [...target.querySelectorAll(".o_command")].map((el) => el.textContent),
                ["Normal", "Blocked", "Done"]
            );
            await click(target, "#o_command_2");
            await nextTick();
            assert.containsN(target, "a.fa-star", 2);
        }
    );
});
