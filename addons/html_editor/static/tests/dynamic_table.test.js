import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { getContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, defineModels, fields, models } from "@web/../tests/web_test_helpers";

import { DYNAMIC_FIELD_PLUGINS } from "@html_editor/backend/dynamic_field/dynamic_field_plugin";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";

describe.current.tags("desktop");

class SomeModel extends models.Model {
    _name = "some.model";

    field = fields.Char({ string: "My little field" });
    partner_ids = fields.One2many({ relation: "partner" });
}

class Partner extends models.Model {
    _name = "partner";

    sub_field = fields.Char({ string: "My sub field" });
}

defineModels([SomeModel, Partner]);

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

test("add dynamic table", async () => {
    const { editor, el } = await setupEditor(`<div>[hop hop]</div>`, getEditorOptions());
    await insertText(editor, "/");
    await contains(".o-we-powerbox .o-we-command-name:contains(/^Dynamic Table$/)").click();
    await contains(".o-dynamic-field-popover .o_model_field_selector_value").click();
    expect(".o_model_field_selector_popover_item_name").toHaveCount(1);

    await contains(".o_model_field_selector_popover_item[data-name='partner_ids'] button").click();
    await contains(".o-dynamic-field-popover button.btn-primary").click();
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
            <table class="table table-sm">
                <tbody>
                    <tr class="border-bottom border-top-0 border-start-0 border-end-0 border-2 border-dark fw-bold">
                        <td>Partners</td>
                    </tr>
                    <tr t-foreach="object.partner_ids" t-as="table_record_0">
                        <td>[Insert a field...]</td>
                    </tr>
                </tbody>
            </table>
        <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
    `)
    );
});

test("dynamic field inside dynamic table", async () => {
    const { editor } = await setupEditor(`<div>[hop hop]</div>`, getEditorOptions());
    await insertText(editor, "/");

    await contains(".o-we-powerbox .o-we-command-name:contains(/^Dynamic Table$/)").click();
    await contains(".o-dynamic-field-popover .o_model_field_selector_value").click();
    await contains(".o_model_field_selector_popover_item[data-name='partner_ids'] button").click();
    await contains(".o-dynamic-field-popover button.btn-primary").click();

    await animationFrame();
    //editor.shared.selection.setSelection({ anchorNode: queryOne(".odoo-editor-editable td:contains(Insert a field...)") });

    await insertText(editor, "/");

    await contains(".o-we-powerbox .o-we-command-name:contains(/^Field$/)").click();

    await contains(".o-dynamic-field-popover .o_model_field_selector_value").click();
    await contains(".o_model_field_selector_popover_page li[data-name='sub_field'] button").click();
    expect(".o-dynamic-field-popover input[name='label_value']").toHaveValue("My sub field");

    await contains(".o-dynamic-field-popover button.btn-primary").click();
});
