/** @odoo-module **/

import { click, clickSave, getFixture } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        bar: { string: "Bar", type: "boolean", default: true },
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
                            bar: true,
                            int_field: 10,
                            trululu: 4,
                        },
                        {
                            id: 2,
                            display_name: "second record",
                        },
                        {
                            id: 3,
                            display_name: "third record",
                        },
                    ],
                    onchanges: {},
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
        target = getFixture();
        setupViewRegistries();
    });

    QUnit.module("RadioField");

    QUnit.test("fieldradio widget on a many2one in a new record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="product_id" widget="radio"/></form>',
        });

        assert.ok(
            target.querySelectorAll("div.o_radio_item").length,
            "should have rendered outer div"
        );
        assert.containsN(target, "input.o_radio_input", 2, "should have 2 possible choices");
        assert.strictEqual(
            target.querySelector(".o_field_radio").textContent.replace(/\s+/g, ""),
            "xphonexpad"
        );
        assert.containsNone(
            target,
            "input.o_radio_input:checked",
            "none of the input should be checked"
        );

        await click(target.querySelectorAll("input.o_radio_input")[0]);

        assert.containsOnce(
            target,
            "input.o_radio_input:checked",
            "one of the input should be checked"
        );

        await clickSave(target);

        assert.hasAttrValue(
            target.querySelector("input.o_radio_input:checked"),
            "data-value",
            "37",
            "should have saved record with correct value"
        );
    });

    QUnit.test("required fieldradio widget on a many2one", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "partner",
            arch: '<form><field name="product_id" widget="radio" required="1"/></form>',
        });

        assert.containsNone(
            target,
            ".o_field_radio input:checked",
            "none of the input should be checked"
        );

        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_notification_title").textContent,
            "Invalid fields: "
        );
        assert.strictEqual(
            target.querySelector(".o_notification_content").innerHTML,
            "<ul><li>Product</li></ul>"
        );
        assert.hasClass(target.querySelector(".o_notification"), "border-danger");
    });

    QUnit.test("fieldradio change value by onchange", async function (assert) {
        serverData.models.partner.onchanges = {
            bar(obj) {
                obj.product_id = obj.bar ? [41] : [37];
                obj.color = obj.bar ? "red" : "black";
            },
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="bar" />
                    <field name="product_id" widget="radio" />
                    <field name="color" widget="radio" />
                </form>`,
        });

        await click(target, ".o_field_boolean input[type='checkbox']");

        assert.containsOnce(
            target,
            "input.o_radio_input[data-value='37']:checked",
            "one of the input should be checked"
        );
        assert.containsOnce(
            target,
            "input.o_radio_input[data-value='black']:checked",
            "the other of the input should be checked"
        );

        await click(target, ".o_field_boolean input[type='checkbox']");
        assert.containsOnce(
            target,
            "input.o_radio_input[data-value='41']:checked",
            "the other of the input should be checked"
        );
        assert.containsOnce(
            target,
            "input.o_radio_input[data-value='red']:checked",
            "one of the input should be checked"
        );
    });

    QUnit.test("fieldradio widget on a selection in a new record", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="color" widget="radio"/></form>',
        });

        assert.ok(
            target.querySelectorAll("div.o_radio_item").length,
            "should have rendered outer div"
        );
        assert.containsN(target, "input.o_radio_input", 2, "should have 2 possible choices");
        assert.strictEqual(
            target.querySelector(".o_field_radio").textContent.replace(/\s+/g, ""),
            "RedBlack"
        );

        // click on 2nd option
        await click(target.querySelectorAll("input.o_radio_input")[1]);

        await clickSave(target);

        assert.hasAttrValue(
            target.querySelector("input.o_radio_input:checked"),
            "data-value",
            "black",
            "should have saved record with correct value"
        );
    });

    QUnit.test("Two RadioField with same selection", async function (assert) {
        serverData.models.partner.fields.color_2 = serverData.models.partner.fields.color;
        serverData.models.partner.records[0].color = "black";
        serverData.models.partner.records[0].color_2 = "black";

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            resId: 1,
            arch: `
            <form>
                <group>
                    <field name="color" widget="radio"/>
                </group>
                <group>
                    <field name="color_2" widget="radio"/>
                </group>
            </form>`,
        });

        assert.hasAttrValue(
            target.querySelector("[name='color'] input.o_radio_input:checked"),
            "data-value",
            "black"
        );
        assert.hasAttrValue(
            target.querySelector("[name='color_2'] input.o_radio_input:checked"),
            "data-value",
            "black"
        );

        // click on Red
        await click(target.querySelector("[name='color_2'] label"));
        assert.hasAttrValue(
            target.querySelector("[name='color'] input.o_radio_input:checked"),
            "data-value",
            "black"
        );
        assert.hasAttrValue(
            target.querySelector("[name='color_2'] input.o_radio_input:checked"),
            "data-value",
            "red"
        );
    });

    QUnit.test("fieldradio widget has o_horizontal or o_vertical class", async function (assert) {
        serverData.models.partner.fields.color2 = serverData.models.partner.fields.color;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <group>
                        <field name="color" widget="radio" />
                        <field name="color2" widget="radio" options="{'horizontal': True}" />
                    </group>
                </form>`,
        });

        assert.containsOnce(
            target,
            ".o_field_radio > div.o_vertical",
            "should have o_vertical class"
        );
        const verticalRadio = target.querySelector(".o_field_radio > div.o_vertical");
        assert.strictEqual(
            verticalRadio.querySelector(".o_radio_item:first-child").getBoundingClientRect().right,
            verticalRadio.querySelector(".o_radio_item:last-child").getBoundingClientRect().right
        );
        assert.containsOnce(
            target,
            ".o_field_radio > div.o_horizontal",
            "should have o_horizontal class"
        );
        const horizontalRadio = target.querySelector(".o_field_radio > div.o_horizontal");
        assert.strictEqual(
            horizontalRadio.querySelector(".o_radio_item:first-child").getBoundingClientRect().top,
            horizontalRadio.querySelector(".o_radio_item:last-child").getBoundingClientRect().top
        );
    });

    QUnit.test("fieldradio widget with numerical keys encoded as strings", async function (assert) {
        assert.expect(5);

        serverData.models.partner.fields.selection = {
            type: "selection",
            selection: [
                ["0", "Red"],
                ["1", "Black"],
            ],
        };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: '<form><field name="selection" widget="radio"/></form>',
            mockRPC: function (route, { args, method, model }) {
                if (model === "partner" && method === "web_save") {
                    assert.strictEqual(args[1].selection, "1", "should write correct value");
                }
            },
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent.replace(/\s+/g, ""),
            "RedBlack"
        );
        assert.containsNone(target, ".o_radio_input:checked", "no value should be checked");

        await click(target.querySelectorAll("input.o_radio_input")[1]);
        await clickSave(target);

        assert.strictEqual(
            target.querySelector(".o_field_widget").textContent.replace(/\s+/g, ""),
            "RedBlack"
        );

        assert.containsOnce(
            target,
            ".o_radio_input[data-index='1']:checked",
            "'Black' should be checked"
        );
    });

    QUnit.test("field is empty", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: `
                <form edit="0">
                    <field name="trululu" widget="radio" />
                </form>`,
        });

        assert.hasClass(target.querySelector(".o_field_widget[name=trululu]"), "o_field_empty");
        assert.containsN(target, ".o_radio_input", 3);
        assert.containsN(target, ".o_radio_input:disabled", 3);
        assert.containsNone(target, ".o_radio_input:checked");
    });
});
