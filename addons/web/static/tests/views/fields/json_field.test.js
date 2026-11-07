/* global ace */

import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    describeJsonError,
    getJsonErrorPosition,
    removeTrailingCommas,
} from "@web/views/fields/json/json_field";
import {
    allowTranslations,
    clickSave,
    contains,
    defineModels,
    editAce,
    fields,
    models,
    mountView,
    onRpc,
    preloadBundle,
    preventResizeObserverError,
} from "@web/../tests/web_test_helpers";

class Product extends models.Model {
    json_field = fields.Json();

    _records = [
        { id: 1, json_field: { tags: ["coupon", "promotion"] } },
        { id: 2, json_field: false },
    ];
}

defineModels([Product]);

preloadBundle("web.ace_lib");
preventResizeObserverError();

test("basic rendering", async () => {
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="json_field"/></form>',
    });
    expect(".o_field_json .ace_editor").toHaveCount(1);
    expect(".o_field_json .ace_editor").toHaveText(/"tags"/);
});

test("readonly rendering", async () => {
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="json_field" readonly="1"/></form>',
    });
    expect(".o_field_json .ace_editor").toHaveCount(1);
    expect(ace.edit(queryOne(".ace_editor")).getReadOnly()).toBe(true);
    expect(".ace_gutter").not.toBeVisible();
});

test("list view displays the compact value", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "product",
        arch: '<list><field name="json_field"/></list>',
    });
    expect(".o_data_cell:first").toHaveText(`{"tags":["coupon","promotion"]}`);
    expect(".o_data_cell:last").toHaveText("");
});

test.tags("focus required");
test("edit and save a valid value", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args[1]);
    });
    await mountView({
        type: "form",
        resModel: "product",
        resId: 2,
        arch: '<form><field name="json_field"/></form>',
    });
    await editAce(`[1, "a", {"b": true}]`);
    await contains(getFixture()).focus(); // blur ace editor
    await clickSave();
    expect.verifySteps([{ json_field: [1, "a", { b: true }] }]);
});

test.tags("focus required");
test("invalid JSON marks the field as invalid", async () => {
    onRpc("web_save", () => {
        throw new Error("should not save an invalid value");
    });
    await mountView({
        type: "form",
        resModel: "product",
        resId: 2,
        arch: '<form><field name="json_field"/></form>',
    });
    await editAce(`{"a": `);
    await contains(getFixture()).focus(); // blur ace editor
    expect(".o_field_json").toHaveClass("o_field_invalid");
    expect(".o_form_button_save").toHaveAttribute("disabled");

    // typing again resets the validity
    await editAce(`{"a": 1}`);
    await animationFrame();
    expect(".o_field_json").not.toHaveClass("o_field_invalid");
});

test("unchanged text does not mark the record as dirty", async () => {
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="json_field"/></form>',
    });
    const editor = ace.edit(queryOne(".ace_editor"));
    const initial = editor.getValue();
    editor.setValue("{}");
    await animationFrame();
    expect(".o_form_status_indicator_buttons").not.toHaveClass("invisible");

    editor.setValue(initial);
    await animationFrame();
    expect(".o_form_status_indicator_buttons").toHaveClass("invisible");
});

test("getJsonErrorPosition handles the browsers error formats", () => {
    const text = `{\n  "a": 1\n  "b": 2\n}`;
    // chrome
    expect(
        getJsonErrorPosition(
            new SyntaxError(
                "Expected ',' or '}' after property value in JSON at position 13 (line 3 column 3)"
            ),
            text
        )
    ).toEqual({ row: 2, column: 2 });
    // firefox
    expect(
        getJsonErrorPosition(
            new SyntaxError(
                "JSON.parse: expected ',' or '}' after property value in object at line 3 column 3 of the JSON data"
            ),
            text
        )
    ).toEqual({ row: 2, column: 2 });
    // position only
    expect(
        getJsonErrorPosition(new SyntaxError("Unexpected token in JSON at position 13"), text)
    ).toEqual({ row: 2, column: 2 });
    // end of input
    expect(
        getJsonErrorPosition(new SyntaxError("Unexpected end of JSON input"), `{\n  "a": \n`)
    ).toEqual({ row: 1, column: 6 });
    // unknown format
    expect(getJsonErrorPosition(new SyntaxError("JSON Parse error: Unexpected"), text)).toEqual({
        row: 0,
        column: 0,
    });
});

test("parsing errors are displayed in the gutter while typing", async () => {
    await mountView({
        type: "form",
        resModel: "product",
        resId: 2,
        arch: '<form><field name="json_field"/></form>',
    });
    const editor = ace.edit(queryOne(".ace_editor"));
    const session = editor.getSession();

    editor.setValue(`{\n  "a": 1\n  "b": 2\n}`);
    await runAllTimers();
    expect(session.getAnnotations()).toHaveLength(1);
    expect(session.getAnnotations()[0]).toMatchObject({ row: 1, type: "error" });
    expect(".o_field_json_error").toHaveText("Line 2: Missing comma");
    // the field is only marked as invalid when leaving the editor
    expect(".o_field_json").not.toHaveClass("o_field_invalid");

    editor.setValue(`{\n  "a": 1,\n  "b": 2\n}`);
    await runAllTimers();
    expect(session.getAnnotations()).toHaveLength(0);
    expect(".o_field_json_error").toHaveCount(0);

    // trailing commas are ignored
    editor.setValue(`{\n  "a": [1,],\n}`);
    await runAllTimers();
    expect(session.getAnnotations()).toHaveLength(0);
    expect(".o_field_json_error").toHaveCount(0);
});

test("describeJsonError locates the most likely error", () => {
    allowTranslations();
    const describe = (text) => {
        try {
            JSON.parse(text);
        } catch (error) {
            return describeJsonError(error, text);
        }
    };
    // missing comma at the end of a line, reported at the end of that line
    expect(describe(`{\n  "a": {},\n  "b": {}\n  "c": 1\n}`)).toEqual({
        row: 2,
        column: 9,
        text: "Missing comma",
    });
    expect(describe(`[\n  1\n  2\n]`)).toEqual({ row: 1, column: 3, text: "Missing comma" });
    // missing comma in the middle of a line
    expect(describe(`{"a": 1 "b": 2}`)).toEqual({ row: 0, column: 8, text: "Missing comma" });
    // other errors keep the browser message, without the position
    const { row, column, text } = describe(`{\n  a: 1\n}`);
    expect({ row, column }).toEqual({ row: 1, column: 2 });
    expect(text).not.toInclude("position");
});

test("removeTrailingCommas ignores the strings content", () => {
    expect(removeTrailingCommas(`[1, 2,]`)).toBe(`[1, 2 ]`);
    expect(removeTrailingCommas(`{\n  "a": {"b": 1,},\n}`)).toBe(`{\n  "a": {"b": 1 } \n}`);
    expect(removeTrailingCommas(`["a,]", "b\\",}"]`)).toBe(`["a,]", "b\\",}"]`);
});

test.tags("focus required");
test("trailing commas are removed on save", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args[1]);
    });
    await mountView({
        type: "form",
        resModel: "product",
        resId: 2,
        arch: '<form><field name="json_field"/></form>',
    });
    await editAce(`{"a": [1, 2,], "b": "c,]",}`);
    await contains(getFixture()).focus(); // blur ace editor
    expect(".o_field_json").not.toHaveClass("o_field_invalid");
    expect(".o_field_json .ace_editor").not.toHaveText(/2,/);
    await clickSave();
    expect.verifySteps([{ json_field: { a: [1, 2], b: "c,]" } }]);
});

test.tags("focus required");
test("discard after an invalid edition restores the value", async () => {
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="json_field"/></form>',
    });
    const editor = ace.edit(queryOne(".ace_editor"));
    const initial = editor.getValue();
    await editAce(`{"a": `);
    await contains(getFixture()).focus(); // blur ace editor
    await runAllTimers();
    expect(".o_field_json").toHaveClass("o_field_invalid");
    expect(".o_field_json_error").toHaveCount(1);

    await contains(".o_form_button_cancel").click();
    await animationFrame();
    expect(editor.getValue()).toBe(initial);
    expect(".o_field_json").not.toHaveClass("o_field_invalid");
    expect(".o_field_json_error").toHaveCount(0);
});

test.tags("focus required");
test("required field accepts scalar values", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args[1]);
    });
    await mountView({
        type: "form",
        resModel: "product",
        resId: 2,
        arch: '<form><field name="json_field" required="1"/></form>',
    });
    for (const value of [42, true, "abc"]) {
        await editAce(JSON.stringify(value));
        await contains(getFixture()).focus(); // blur ace editor
        await clickSave();
        expect(".o_field_json").not.toHaveClass("o_field_invalid");
        expect.verifySteps([{ json_field: value }]);
    }
    // empty objects are still considered as unset
    await editAce("{}");
    await contains(getFixture()).focus(); // blur ace editor
    await clickSave();
    expect(".o_field_json").toHaveClass("o_field_invalid");
    expect.verifySteps([]);
});

test("the editor is limited to 3 lines in an editable list", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "product",
        arch: '<list editable="bottom"><field name="json_field"/></list>',
    });
    await contains(".o_data_cell:first").click();
    expect(".o_data_row .ace_editor").toHaveCount(1);
    expect(ace.edit(queryOne(".o_data_row .ace_editor")).getOption("maxLines")).toBe(3);
});

test("readonly cells of a list display the compact value", async () => {
    onRpc("has_group", () => true);
    await mountView({
        type: "list",
        resModel: "product",
        arch: `
            <list editable="bottom">
                <field name="json_field" widget="json"/>
                <field name="json_field" readonly="1"/>
            </list>`,
    });
    // explicit widget, row not in edition
    expect(".ace_editor").toHaveCount(0);
    expect(".o_data_row:first .o_data_cell:eq(0)").toHaveText(`{"tags":["coupon","promotion"]}`);

    // row in edition: the editor is only used for the editable column
    await contains(".o_data_row:first .o_data_cell:eq(0)").click();
    expect(".o_data_row:first .o_data_cell:eq(0) .ace_editor").toHaveCount(1);
    expect(".o_data_row:first .o_data_cell:eq(1) .ace_editor").toHaveCount(0);
    expect(".o_data_row:first .o_data_cell:eq(1)").toHaveText(`{"tags":["coupon","promotion"]}`);
});
