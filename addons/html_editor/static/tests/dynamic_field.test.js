import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { getContent } from "@html_editor/../tests/_helpers/selection";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, press, queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, defineModels, fields, models } from "@web/../tests/web_test_helpers";

import { DYNAMIC_FIELD_PLUGINS } from "@html_editor/backend/dynamic_field/dynamic_field_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";

describe.current.tags("desktop");

class SomeModel extends models.Model {
    _name = "some.model";

    field = fields.Char({ string: "My little field" });
}

defineModels([SomeModel]);

function getEditorOptions() {
    return {
        config: {
            Plugins: [...MAIN_PLUGINS, ...DYNAMIC_FIELD_PLUGINS],
            classList: ["odoo-editor-qweb"],
            dynamicResModel: "some.model",
        },
        props: {
            iframe: true,
            copyCss: true,
        },
    };
}

test("add dynamic field", async () => {
    const { editor, el } = await setupEditor(`<div>[hop hop]</div>`, getEditorOptions());
    await insertText(editor, "/");
    await contains(".o-we-powerbox .o-we-command-name:contains(/^Field$/)").click();

    await contains(".o-dynamic-field-popover .o_model_field_selector_value").click();
    await contains(".o_model_field_selector_popover_page li[data-name='field'] button").click();
    expect(".o-dynamic-field-popover input[name='label_value']").toHaveValue("My little field");

    await contains(".o-dynamic-field-popover button.btn-primary").click();
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
            <div class="o-paragraph">
                <t data-oe-expression-readable="My little field" t-out="object.field" data-oe-demo="My little field" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">My little field</t>[]
            </div>
        <p data-selection-placeholder=""><br></p>
    `)
    );
});

test("select all fields", async () => {
    const { el } = await setupEditor(
        `<div>a<t t-out="object.field" data-oe-expression-readable="human > expr"></t></div>`,
        getEditorOptions()
    );
    await contains(":iframe t[t-out]").click();
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder=""><br></p>` +
            `<div>a[<t t-out="object.field" data-oe-expression-readable="human > expr" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">human > expr</t>]</div>` +
            `<p data-selection-placeholder=""><br></p>`
    );
});

test("copy field", async () => {
    const options = getEditorOptions();
    // Disable iframe for now: seems that hoot.press doesn't properly handle it.
    options.props.iframe = false;

    const { editor, el } = await setupEditor(
        `<div>a<t t-out="object.field" data-oe-expression-readable="human ... expr"></t></div>`,
        options
    );
    el.focus();
    await contains("t[t-out]").click();
    const clipboardData = new DataTransfer();
    await press(["ctrl", "c"], { dataTransfer: clipboardData });
    expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
        `<t t-out="object.field" data-oe-expression-readable="human ... expr" data-oe-protected="true" contenteditable="false"></t>`
    );

    editor.shared.selection.setSelection({ anchorNode: queryOne(".odoo-editor-editable div") });
    await manuallyDispatchProgrammaticEvent(el, "paste", { clipboardData });

    expect(getContent(el)).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p>` +
                `<div>` +
                `<t t-out="object.field" data-oe-expression-readable="human ... expr" data-oe-protected="true" contenteditable="false" data-oe-t-inline="true">human ... expr</t>[]a` +
                `<t t-out="object.field" data-oe-expression-readable="human ... expr" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">human ... expr</t>` +
                `</div>` +
                `<p data-selection-placeholder=""><br></p>`
        )
    );
});

test("edit fields and back", async () => {
    const { editor, el } = await setupEditor(
        `<div>a<t t-out="object.field" data-oe-expression-readable="human > expr" data-oe-demo="demo brol"></t></div>`,
        getEditorOptions()
    );
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder=""><br></p><div>a<t t-out="object.field" data-oe-expression-readable="human > expr" data-oe-demo="demo brol" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">demo brol</t></div><p data-selection-placeholder=""><br></p>`
    );

    await contains(":iframe t[t-out]").click();
    await contains(".o-we-toolbar button[name='editDynamicField']").click();
    await contains(".o-dynamic-field-popover .o_model_field_selector_value").click();
    await contains(
        ".o_model_field_selector_popover_page li[data-name='display_name'] button"
    ).click();
    await contains(".o-dynamic-field-popover input[name='label_value']").edit("edited", {
        confirm: false,
    });
    await contains(".o-dynamic-field-popover button.btn-primary").click();

    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
            <div>a[<t t-out="object.display_name" data-oe-expression-readable="Display name" data-oe-demo="edited" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">edited</t>]</div>
        <p data-selection-placeholder=""><br></p>
    `)
    );

    expect(getContent(editor.getElContent())).toBe(
        unformat(`
        <div>a<t t-out="object.display_name" data-oe-expression-readable="Display name" data-oe-demo="edited"></t></div>
    `)
    );

    editor.shared.history.undo();
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder=""><br></p>` +
            `<div>[]a<t t-out="object.field" data-oe-expression-readable="human > expr" data-oe-demo="demo brol" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">demo brol</t></div>` +
            `<p data-selection-placeholder=""><br></p>`
    );
});

test("inserted value from dynamic field should contain the data-oe-t-inline attribute", async () => {
    const { editor } = await setupEditor("<p>test[]</p>", {
        config: {
            Plugins: [...MAIN_PLUGINS, ...DYNAMIC_FIELD_PLUGINS],
            dynamicResModel: "some.model",
        },
    });
    await insertText(editor, "/");
    await contains(".o-we-powerbox .o-we-command-name:contains(/^Field$/)").click();

    await contains(".o-dynamic-field-popover .o_model_field_selector_value").click();
    await contains(".o_model_field_selector_popover_page li[data-name='field'] button").click();
    expect(".o-dynamic-field-popover input[name='label_value']").toHaveValue("My little field");

    await contains(".o-dynamic-field-popover button.btn-primary").click();
    await animationFrame();

    expect("t[data-oe-t-inline]").toHaveCount(1);
});
