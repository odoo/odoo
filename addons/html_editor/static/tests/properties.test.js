import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";

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
            properties: { bd6404492c244cff: "<b> test </b>" },
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
                    name: "bd6404492c244cff",
                    type: "html",
                },
            ],
        },
    ];
}

defineModels([Partner, User]);

test("properties: html", async () => {
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
});

test("properties: html readonly", async () => {
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
