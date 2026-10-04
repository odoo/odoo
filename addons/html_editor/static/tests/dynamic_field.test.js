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

class OneModel extends models.Model {
    name = fields.Char({ string: "The many2one model name" });
}

class SomeModel extends models.Model {
    _name = "some.model";

    field = fields.Char({ string: "My little field" });
    many2one_model_id = fields.Many2one({ relation: "one.model" });
    product_id = fields.Many2one({ relation: "product" });
    properties = fields.Properties({
        string: "Properties",
        definition_record: "product_id",
        definition_record_field: "properties_definitions",
    });
}

class Product extends models.Model {
    name = fields.Char({ string: "Product Name" });
    properties_definitions = fields.PropertiesDefinition();

    _records = [
        {
            id: 1,
            name: "xphone",
            properties_definitions: [
                {
                    name: "property_partner",
                    type: "many2one",
                    string: "Partner Property",
                    comodel: "res.partner",
                },
            ],
        },
    ];
}

class Partner extends models.Model {
    _name = "res.partner";

    name = fields.Char({ string: "Partner Name" });
}

defineModels([OneModel, SomeModel, Product, Partner]);

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

test("add dynamic field with relational property", async () => {
    const { editor, el } = await setupEditor(`<div>[hop hop]</div>`, getEditorOptions());
    await insertText(editor, "/");
    await contains(".o-we-powerbox .o-we-command-name:contains(/^Field$/)").click();

    await contains(".o-dynamic-field-popover .o_model_field_selector_value").click();
    await contains(
        "li[data-name='properties'] .o_model_field_selector_popover_item_relation"
    ).click();
    expect(".o-dynamic-field-popover button.btn-primary").not.toBeEnabled();
    await contains(
        "li[data-name='property_partner'] .o_model_field_selector_popover_item_relation"
    ).click();
    expect(".o-dynamic-field-popover .o_model_field_selector_chain_part").toHaveCount(1);
    expect(".o-dynamic-field-popover .o_model_field_selector_chain_part").toHaveText(
        "properties.get('property_partner', env['res.partner'])"
    );
    await contains("li[data-name='name'] button:contains('Partner Name')").click();
    expect("input[name='label_value']").toHaveValue("Partner Name");

    await contains(".o-dynamic-field-popover button.btn-primary").click();
    await animationFrame();
    expect(getContent(el)).toInclude("Partner Name");
    expect(getContent(el)).toInclude(
        `t-out="object.properties.get('property_partner', env['res.partner']).name"`
    );
});

test("add many2one dynamic field should take the name by default", async () => {
    const { editor, el } = await setupEditor(`<div>[hop hop]</div>`, getEditorOptions());
    await insertText(editor, "/");
    await contains(".o-we-powerbox .o-we-command-name:contains(/^Field$/)").click();

    await contains(".o-dynamic-field-popover .o_model_field_selector_value").click();
    await contains(
        ".o_model_field_selector_popover_page li[data-name='many2one_model_id'] button"
    ).click();
    expect(".o-dynamic-field-popover input[name='label_value']").toHaveValue("Many2one model");

    await contains(".o-dynamic-field-popover button.btn-primary").click();
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
            <div class="o-paragraph">
                <t data-oe-expression-readable="Display name" t-out="object.many2one_model_id.display_name" data-oe-demo="Many2one model" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false">Many2one model</t>[]
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

    // data-oe-demo/data-oe-expression-readable are editor-only metadata: they
    // must not survive a save, but the (possibly user-edited) content is kept.
    expect(getContent(editor.getElContent())).toBe(
        unformat(`
        <div>a<t t-out="object.display_name">edited</t></div>
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

test("cleaning removes dummy attributes but keeps the fallback content", async () => {
    // the node has no content: normalizeQwebPlaceholders backfills it with the
    // data-oe-demo value, which must survive the save as the t-out fallback text
    // while the data-oe-demo/data-oe-expression-readable attributes must not.
    const { editor } = await setupEditor(
        `<div>a<t t-out="object.field" data-oe-expression-readable="human > expr" data-oe-demo="demo brol"></t></div>`,
        getEditorOptions()
    );

    expect(getContent(editor.getElContent())).toBe(
        unformat(`
            <div>a<t t-out="object.field">demo brol</t></div>
        `)
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

test("cannot insert or edit a dynamic field without a model", async () => {
    const options = getEditorOptions();
    options.config.dynamicResModel = "";
    // Verify insert
    const { editor } = await setupEditor("<p>[]</p>", options);
    await insertText(editor, "/");
    await contains(".o-we-powerbox .o-we-command-name:contains(/^Field$/)").click();

    expect(".o_notification").toHaveText(
        "Oops! Select a model for this template before inserting fields."
    );
    expect(".o-dynamic-field-popover").toHaveCount(0);
    await contains(".o_notification .btn-close").click();

    // Verify edit
    await setupEditor(
        `<div><t t-out="object.field" data-oe-expression-readable="My little field" data-oe-demo="My little field"></t></div>`,
        options
    );
    await contains(":iframe t[t-out]").click();
    await contains(".o-we-toolbar button[name='editDynamicField']").click();

    expect(".o_notification").toHaveText(
        "Oops! Select a model for this template before editing fields."
    );
    expect(".o-dynamic-field-popover").toHaveCount(0);
});
