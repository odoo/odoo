/** @odoo-module **/

import { click, editInput } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        int_field: {
                            string: "int_field",
                            type: "integer",
                        },
                    },
                    records: [
                        { id: 1, int_field: 10 },
                        { id: 2, int_field: false },
                        { id: 3, int_field: 8069 },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("IntegerField");

    QUnit.test("should be 0 when unset", async function (assert) {
        assert.expect(2);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 2,
            arch: '<form><field name="int_field"/></form>',
        });

        assert.doesNotHaveClass(
            form.el.querySelector(".o_field_widget"),
            "o_field_empty",
            "Non-set integer field should be recognized as 0."
        );

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "0",
            "Non-set integer field should be recognized as 0."
        );
    });

    QUnit.test("basic form view flow", async function (assert) {
        assert.expect(3);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="int_field"/></form>',
        });

        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector("input[name=int_field]").value,
            "10",
            "The value should be rendered correctly in edit mode."
        );

        await editInput(form.el, "input[name=int_field]", "30");

        assert.strictEqual(
            form.el.querySelector("input[name=int_field]").value,
            "30",
            "The value should be correctly displayed in the input."
        );

        await click(form.el, ".o_form_button_save");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "30",
            "The new value should be saved and displayed properly."
        );
    });

    QUnit.test("rounded when using formula in form view", async function (assert) {
        assert.expect(1);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: '<form><field name="int_field"/></form>',
        });

        await click(form.el, ".o_form_button_edit");
        await editInput(form.el, "input[name=int_field]", "=100/3");
        await click(form.el, ".o_form_button_save");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "33",
            "The new value should be calculated properly."
        );
    });

    QUnit.test("with input type 'number' option", async function (assert) {
        assert.expect(4);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="int_field" options="{'type': 'number'}"/></form>`,
        });

        await click(form.el, ".o_form_button_edit");

        assert.ok(
            form.el.querySelector(".o_field_widget").hasAttribute("type"),
            "Integer field with option type must have a type attribute."
        );

        assert.hasAttrValue(
            form.el.querySelector(".o_field_widget"),
            "type",
            "number",
            'Integer field with option type must have a type attribute equals to "number".'
        );

        await editInput(form.el, "input[name=int_field]", "1234567890");
        await click(form.el, ".o_form_button_save");
        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").value,
            "1234567890",
            "Integer value must be not formatted if input type is number."
        );

        await click(form.el, ".o_form_button_save");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "1,234,567,890",
            "Integer value must be formatted in readonly view even if the input type is number."
        );
    });

    QUnit.test("without input type option", async function (assert) {
        assert.expect(2);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `<form><field name="int_field"/></form>`,
        });

        await click(form.el, ".o_form_button_edit");

        assert.hasAttrValue(
            form.el.querySelector(".o_field_widget"),
            "type",
            "text",
            "Integer field without option type must have a text type (default type)."
        );

        await editInput(form.el, "input[name=int_field]", "1234567890");
        await click(form.el, ".o_form_button_save");
        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").value,
            "1,234,567,890",
            "Integer value must be formatted if input type isn't number."
        );
    });

    QUnit.test("with disable formatting option", async function (assert) {
        assert.expect(2);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 3,
            arch: `<form><field name="int_field"  options="{'format': 'false'}"/></form>`,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=int_field]").textContent,
            "8069",
            "Integer value must not be formatted"
        );

        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").value,
            "8069",
            "Integer value must not be formatted"
        );
    });

    QUnit.test("IntegerField is formatted by default", async function (assert) {
        assert.expect(2);

        var form = await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 3,
            arch: `<form><field name="int_field"/></form>`,
        });

        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name=int_field]").textContent,
            "8,069",
            "Integer value must be formatted by default"
        );

        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").value,
            "8,069",
            "Integer value must be formatted by default"
        );
    });

    // should we keep the next one ? This is bad.
    QUnit.skip("IntegerField in form view with virtual id", async function (assert) {
        assert.expect(1);

        var params = {
            type: "form",
            serverData,
            resModel: "partner",
            arch: '<form><field name="int_field"/></form>',
        };
        params.resId = serverData.models.partner.records[1].id = "2-20170808020000";
        var form = await makeView(params);

        assert.strictEqual(
            form.el.querySelector(".o_field_widget").textContent,
            "2-20170808020000",
            "Should display virtual id"
        );
    });

    QUnit.skip("basic flow in editable list view", async function (assert) {
        assert.expect(4);

        var list = await createView({
            View: ListView,
            model: "partner",
            data: this.data,
            arch: '<tree editable="bottom">' + '<field name="int_field"/>' + "</tree>",
        });

        var zeroValues = list.$("td").filter(function () {
            return $(this).text() === "0";
        });
        assert.strictEqual(
            zeroValues.length,
            1,
            "Unset integer values should not be rendered as zeros."
        );

        // switch to edit mode
        var $cell = list.$("tr.o_data_row td:not(.o_list_record_selector)").first();
        await testUtils.dom.click($cell);

        assert.containsOnce(
            list,
            'input[name="int_field"]',
            "The view should have 1 input for editable integer."
        );

        await testUtils.fields.editInput(list.$('input[name="int_field"]'), "-28");
        assert.strictEqual(
            list.$('input[name="int_field"]').val(),
            "-28",
            "The value should be displayed properly in the input."
        );

        await testUtils.dom.click(list.$buttons.find(".o_list_button_save"));
        assert.strictEqual(
            list.$("td:not(.o_list_record_selector)").first().text(),
            "-28",
            "The new value should be saved and displayed properly."
        );

        list.destroy();
    });
});
