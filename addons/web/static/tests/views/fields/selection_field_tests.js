/** @odoo-module **/

import { click, clickSave, editSelect, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
                        product_id: { string: "Product", type: "many2one", relation: "product" },
                        color: {
                            type: "selection",
                            selection: [
                                ["red", "Red"],
                                ["black", "Black"],
                            ],
                            default: "red",
                            string: "Color",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            int_field: 10,
                            trululu: 4,
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            int_field: 9,
                            trululu: 1,
                            product_id: 37,
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                        },
                    ],
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("SelectionField");

    QUnit.test("SelectionField in a list view", async function (assert) {
        serverData.models.partner.records.forEach(function (r) {
            r.color = "red";
        });

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: '<tree string="Colors" editable="top"><field name="color"/></tree>',
        });

        assert.containsN(target, ".o_data_row", 3);
        await click(target.querySelector(".o_data_cell"));

        const td = target.querySelector("tbody tr.o_selected_row td:not(.o_list_record_selector)");
        assert.containsOnce(td, "select", "td should have a child 'select'");
        assert.strictEqual(td.children.length, 1, "select tag should be only child of td");
    });

    QUnit.test("SelectionField, edition and on many2one field", async function (assert) {
        serverData.models.partner.onchanges = { product_id: function () {} };
        serverData.models.partner.records[0].product_id = 37;
        serverData.models.partner.records[0].trululu = false;

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="product_id" widget="selection" />
                    <field name="trululu" widget="selection" />
                    <field name="color" widget="selection" />
                </form>`,
            mockRPC(route, { method }) {
                assert.step(method);
            },
        });

        assert.containsN(target, "select", 3);
        assert.containsOnce(
            target,
            ".o_field_widget[name='product_id'] select option[value='37']",
            "should have fetched xphone option"
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name='product_id'] select option[value='41']",
            "should have fetched xpad option"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id'] select").value,
            "37",
            "should have correct product_id value"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='trululu'] select").value,
            "false",
            "should not have any value in trululu field"
        );

        await editSelect(target, ".o_field_widget[name='product_id'] select", "41");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='product_id'] select").value,
            "41",
            "should have a value of xphone"
        );

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='color'] select").value,
            `"red"`,
            "should have correct value in color field"
        );

        assert.verifySteps(["get_views", "web_read", "name_search", "name_search", "onchange"]);
    });

    QUnit.test("unset selection field with 0 as key", async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists.
        serverData.models.partner.fields.selection = {
            type: "selection",
            selection: [
                [0, "Value O"],
                [1, "Value 1"],
            ],
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form edit="0"><field name="selection" /></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "Value O",
            "the displayed value should be 'Value O'"
        );
        assert.doesNotHaveClass(
            target.querySelector(".o_field_widget"),
            "o_field_empty",
            "should not have class o_field_empty"
        );
    });

    QUnit.test("unset selection field with string keys", async function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists. In
        // this test, it doesn't exist as keys are strings.
        serverData.models.partner.fields.selection = {
            type: "selection",
            selection: [
                ["0", "Value O"],
                ["1", "Value 1"],
            ],
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form edit="0"><field name="selection" /></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent,
            "",
            "there should be no displayed value"
        );
        assert.hasClass(
            target.querySelector(".o_field_widget"),
            "o_field_empty",
            "should have class o_field_empty"
        );
    });

    QUnit.test("unset selection on a many2one field", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="trululu" widget="selection" /></form>',
            mockRPC(route, { args, method }) {
                if (method === "web_save") {
                    assert.strictEqual(
                        args[1].trululu,
                        false,
                        "should send 'false' as trululu value"
                    );
                }
            },
        });

        await editSelect(target, ".o_form_view select", "false");
        await clickSave(target);
    });

    QUnit.test("field selection with many2ones and special characters", async function (assert) {
        // edit the partner with id=4
        serverData.models.partner.records[2].display_name = "<span>hey</span>";

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="trululu" widget="selection" /></form>',
        });

        assert.strictEqual(
            target.querySelector("select option[value='4']").textContent,
            "<span>hey</span>"
        );
    });

    QUnit.test("required selection widget should not have blank option", async function (assert) {
        serverData.models.partner.fields.feedback_value = {
            type: "selection",
            required: true,
            selection: [
                ["good", "Good"],
                ["bad", "Bad"],
            ],
            default: "good",
            string: "Good",
        };
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="feedback_value" />
                    <field name="color" required="feedback_value == 'bad'" />
                </form>`,
        });

        assert.deepEqual(
            [...target.querySelectorAll(".o_field_widget[name='color'] option")].map(
                (option) => option.style.display
            ),
            ["", "", ""]
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_widget[name='feedback_value'] option")].map(
                (option) => option.style.display
            ),
            ["none", "", ""]
        );

        // change value to update widget modifier values
        await editSelect(target, ".o_field_widget[name='feedback_value'] select", '"bad"');
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_widget[name='color'] option")].map(
                (option) => option.style.display
            ),
            ["none", "", ""]
        );
    });

    QUnit.test(
        "required selection widget should have only one blank option",
        async function (assert) {
            serverData.models.partner.fields.feedback_value = {
                type: "selection",
                required: true,
                selection: [
                    ["good", "Good"],
                    ["bad", "Bad"],
                ],
                default: "good",
                string: "Good",
            };
            serverData.models.partner.fields.color.selection = [
                [false, ""],
                ...serverData.models.partner.fields.color.selection,
            ];

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                <form>
                    <field name="feedback_value" />
                    <field name="color" required="feedback_value == 'bad'" />
                </form>`,
            });

            assert.containsN(
                target.querySelector(".o_field_widget[name='color']"),
                "option",
                3,
                "Three options in non required field (one blank option)"
            );

            // change value to update widget modifier values
            await editSelect(target, ".o_field_widget[name='feedback_value'] select", '"bad"');
            assert.deepEqual(
                [...target.querySelectorAll(".o_field_widget[name='color'] option")].map(
                    (option) => option.style.display
                ),
                ["none", "", ""]
            );
        }
    );

    QUnit.test("selection field with placeholder", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="trululu" widget="selection" placeholder="Placeholder"/>
                </form>`,
        });

        const placeholderOption = target.querySelector(
            ".o_field_widget[name='trululu'] select option"
        );
        assert.strictEqual(placeholderOption.textContent, "Placeholder");
        assert.strictEqual(placeholderOption.value, "false");
    });

    QUnit.test("SelectionField in kanban view", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="color" widget="selection" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            domain: [["id", "=", 1]],
        });

        assert.containsOnce(
            target,
            ".o_field_widget[name='color'] select",
            "SelectionKanbanField widget applied to selection field"
        );

        assert.containsN(
            target.querySelector(".o_field_widget[name='color']"),
            "option",
            3,
            "Three options are displayed (one blank option)"
        );
        assert.deepEqual(
            [...target.querySelectorAll(".o_field_widget[name='color'] option")].map(
                (option) => option.value
            ),
            ["false", "\"red\"", "\"black\""]
        );
    });

    QUnit.test("SelectionField - auto save record in kanban view", async function (assert) {
        assert.expect(2);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="color" widget="selection" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            domain: [["id", "=", 1]],
            mockRPC(_route, { method }) {
                if (method === "web_save") {
                    assert.step("web_save");
                }
            },
        });
        await editSelect(target, ".o_field_widget[name='color'] select", '"black"');
        assert.verifySteps(["web_save"]);
    });

    QUnit.test(
        "SelectionField don't open form view on click in kanban view",
        async function (assert) {
        assert.expect(1);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="color" widget="selection" />
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            domain: [["id", "=", 1]],
            selectRecord: () => {
                assert.step("selectRecord");
            },
        });

        await click(target, ".o_field_widget[name='color'] select");
        assert.verifySteps([]);
    });

    QUnit.test("SelectionField is disabled if field readonly", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.color.readonly = true;

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="color" widget="selection" />
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            domain: [["id", "=", 1]],
        });

        assert.containsOnce(
            target,
            ".o_field_widget[name='color'] span",
            "field should be readonly"
        );
    });

    QUnit.test("SelectionField is disabled with a readonly attribute", async function (assert) {
        assert.expect(1);

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="color" widget="selection" readonly="1" />
                            </div>
                        </t>
                    </templates>
                </kanban>
            `,
            domain: [["id", "=", 1]],
        });

        assert.containsOnce(
            target,
            ".o_field_widget[name='color'] span",
            "field should be readonly"
        );
    });
});
