import { expect, test } from "@odoo/hoot";
import { animationFrame, queryAllTexts } from "@odoo/hoot-dom";
import { followRelation } from "@web/../tests/core/tree_editor/condition_tree_editor_test_helpers";
import { contains, defineModels, fields, models, mountView } from "../../web_test_helpers";

class Contact extends models.Model {
    email = fields.Char();
    child_ids = fields.One2many({ relation: "contact" });
}

class Lead extends models.Model {
    contact_id = fields.Many2one({ relation: "contact" });
    salesperson_id = fields.Many2one({ relation: "contact" });
    note = fields.Text();
}

class UpdateRecordAction extends models.Model {
    model = fields.Char();
    update_path = fields.Char();
    non_searchable = fields.Char({ searchable: false });
}

defineModels([Contact, Lead, UpdateRecordAction]);

test("readonly", async () => {
    UpdateRecordAction._records = [
        {
            id: 1,
            update_path: "non_searchable",
        },
    ];
    await mountView({
        type: "form",
        resModel: "update.record.action",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="update_path" widget="field_selector" readonly="1"/>
            </form>
        `,
    });
    expect(".o_field_widget[name='update_path']").toHaveText("non_searchable");
    expect(".o_field_widget[name='update_path']").toHaveClass(
        "o_field_widget o_readonly_modifier o_field_field_selector"
    );
    expect(".o_field_widget[name='update_path'] .o_input").toHaveCount(0);
});

test("no specified options", async () => {
    await mountView({
        type: "form",
        resModel: "update.record.action",
        arch: /* xml */ `
            <form>
                <field name="update_path" widget="field_selector"/>
            </form>
        `,
    });
    await contains(".o_field_widget[name='update_path'] .o_input").click();
    expect(queryAllTexts(".o_model_field_selector_popover_item")).toEqual(
        [
            "Created on",
            "Display name",
            "Id",
            "Last Modified on",
            "Model",
            "Non searchable",
            "Update path",
        ],
        { message: "should display fields from same model by default" }
    );
});

test("only_searchable option", async () => {
    await mountView({
        type: "form",
        resModel: "update.record.action",
        arch: /* xml */ `
            <form>
                <field name="update_path" widget="field_selector" options="{'only_searchable': true}"/>
            </form>
        `,
    });
    await contains(".o_field_widget[name='update_path'] .o_input").click();
    expect(queryAllTexts(".o_model_field_selector_popover_item")).toEqual(
        ["Created on", "Display name", "Id", "Last Modified on", "Model", "Update path"],
        { message: "should not display non searchable fields" }
    );
});

test("model option", async () => {
    await mountView({
        type: "form",
        resModel: "update.record.action",
        arch: /* xml */ `
            <form>
                <field name="model"/>
                <field name="update_path" widget="field_selector" options="{'model': 'model'}"/>
            </form>
        `,
    });
    await contains(".o_field_widget[name='update_path'] .o_input").click();
    expect(queryAllTexts(".o_model_field_selector_popover_item")).toEqual(
        [
            "Created on",
            "Display name",
            "Id",
            "Last Modified on",
            "Model",
            "Non searchable",
            "Update path",
        ],
        { message: "should display fields from same model by default" }
    );
    await contains(".o_field_widget[name='model'] .o_input").edit("lead");
    await contains(".o_field_widget[name='update_path'] .o_input").click();
    expect(queryAllTexts(".o_model_field_selector_popover_item")).toEqual(
        ["Contact", "Created on", "Display name", "Id", "Last Modified on", "Note", "Salesperson"],
        { message: "should display fields of the specified model" }
    );
    expect(".o_model_field_selector_popover_item_relation").toHaveCount(2, {
        message: "following relations is supported by default",
    });
    await followRelation();
    await animationFrame();
    expect(queryAllTexts(".o_model_field_selector_popover_item")).toEqual(
        ["Childs", "Created on", "Display name", "Email", "Id", "Last Modified on"],
        { message: "should display fields of the selected relation" }
    );
});

test("follow_relations option", async () => {
    await mountView({
        type: "form",
        resModel: "update.record.action",
        arch: /* xml */ `
            <form>
                <field name="model"/>
                <field name="update_path" widget="field_selector" options="{
                    'model': 'model',
                    'follow_relations': false,
                }"/>
            </form>
        `,
    });
    await contains(".o_field_widget[name='model'] .o_input").edit("lead");
    await contains(".o_field_widget[name='update_path'] .o_input").click();
    expect(queryAllTexts(".o_model_field_selector_popover_item")).toEqual(
        ["Contact", "Created on", "Display name", "Id", "Last Modified on", "Note", "Salesperson"],
        { message: "should display fields of the specified model" }
    );
    expect(".o_model_field_selector_popover_item_relation").toHaveCount(0, {
        message: "should not allow to follow relations",
    });
});
