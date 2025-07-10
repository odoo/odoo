import { expect, test } from "@odoo/hoot";
import {
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
    contains,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { htmlEditorVersions } from "@html_editor/html_migrations/html_migrations_utils";
import { PropertyValue } from "@web/views/fields/properties/property_value";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { queryOne } from "@odoo/hoot-dom";

const VERSIONS = htmlEditorVersions();
const CURRENT_VERSION = VERSIONS.at(-1);

class Partner extends models.Model {
    _name = "res.partner";
    user_id = fields.Many2one({ relation: "res.users" });

    properties = fields.Properties({
        definition_record: "user_id",
        definition_record_field: "properties_definitions",
    });

    _records = [
        {
            id: 1,
            user_id: 1,
            properties: { bd6404492c244cff_html: "<b> test </b>" },
        },
        {
            id: 2,
            user_id: 1,
            properties: {
                bd6404492c244cff_html: `<p>Hello World</p><div data-embedded="draw" data-embedded-props='{"source": "https://excalidraw.com"}'/>`,
            },
        },
        {
            id: 3,
            user_id: 1,
            properties: {}, // Property not set
        },
    ];
}

class User extends models.Model {
    _name = "res.users";

    properties_definitions = fields.PropertiesDefinition();

    _records = [
        {
            id: 1,
            properties_definitions: [
                {
                    name: "bd6404492c244cff_html",
                    type: "html",
                    string: "HTML Property",
                },
            ],
        },
    ];
}

defineModels([Partner, User]);

test("properties: html", async () => {
    patchWithCleanup(user, { hasGroup: (group) => false });
    let editor;
    patchWithCleanup(PropertyValue.prototype, {
        onEditorLoad(ed) {
            super.onEditorLoad(ed);
            editor = ed;
        },
    });
    await mountView({
        type: "form",
        resId: 1,
        resModel: "res.partner",
        arch: `
            <form>
                <field name="user_id"/>
                <field name="properties"/>
            </form>`,
    });
    expect(`[name="properties"] .odoo-editor-editable`).toHaveCount(1);
    expect(`[name="properties"] .odoo-editor-editable .o-paragraph`).toHaveInnerHTML(
        "<b> test </b>"
    );

    setSelection({
        anchorNode: queryOne(`[name="properties"] .odoo-editor-editable .o-paragraph b`),
        anchorOffset: 0,
    });
    await insertText(editor, " foo");
    expect(`[name="properties"] .odoo-editor-editable .o-paragraph`).toHaveInnerHTML(
        "<b> foo test </b>"
    );

    // Ensure the shown value isn't replaced by escaped HTML upon saving the form.
    // Blur to show the save button.
    await contains(".o_field_property_label").click();
    await contains(".o_form_button_save").click();
    expect(`[name="properties"] .odoo-editor-editable .o-paragraph`).toHaveInnerHTML(
        "<b> foo test </b>"
    );
});

test("properties: html migration", async () => {
    patchWithCleanup(user, { hasGroup: (group) => false });
    let component;
    patchWithCleanup(PropertyValue.prototype, {
        setup() {
            super.setup();
            component = this;
        },
    });

    await mountView({
        type: "form",
        resId: 2,
        resModel: "res.partner",
        arch: `
            <form>
                <field name="user_id"/>
                <field name="properties"/>
            </form>`,
    });
    expect(`[name="properties"] .odoo-editor-editable`).toHaveCount(1);
    expect(`[name="properties"] .odoo-editor-editable a[href*="excalidraw.com"]`).toHaveCount(1);
    expect(component.editor.getContent()).toBe(
        `<p data-oe-version="${CURRENT_VERSION}">Hello World</p><p><a href="https://excalidraw.com">https://excalidraw.com</a></p>`
    );
});

test("properties: html readonly", async () => {
    patchWithCleanup(user, { hasGroup: (group) => false });
    await mountView({
        type: "form",
        resId: 1,
        resModel: "res.partner",
        arch: `
            <form>
                <field name="user_id"/>
                <field name="properties" readonly="1"/>
            </form>`,
    });
    expect(".odoo-editor-editable").toHaveCount(0);
    expect(`[name="properties"] .o_readonly`).toHaveCount(1);
    expect(`[name="properties"] iframe`).toHaveCount(1);
});

test("properties: html in list view", async () => {
    patchWithCleanup(user, { hasGroup: (group) => false });
    await mountView({
        resModel: "res.partner",
        type: "list",
        arch: `
            <list>
                <field name="user_id"/>
                <field name="properties"/>
            </list>
        `,
    });
    await contains(".o_optional_columns_dropdown_toggle").click();
    await contains(".o-dropdown--menu input[type='checkbox']").click();
    expect("div[name='properties.bd6404492c244cff_html']").toHaveCount(3);
    const elements = document.querySelectorAll("div[name='properties.bd6404492c244cff_html']");
    expect(elements[0].innerText).toBe("test");
    expect(elements[1].innerText).toBe("Hello World\n\nhttps://excalidraw.com");
    expect(elements[2].innerText).toBe("");
});
