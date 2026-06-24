import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { click, manuallyDispatchProgrammaticEvent, press, queryFirst } from "@odoo/hoot-dom";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { DYNAMIC_PLACEHOLDER_PLUGINS } from "@html_editor/backend/plugin_sets";
import { unformat } from "@html_editor/../tests/_helpers/format";
import { getContent } from "@html_editor/../tests/_helpers/selection";
import {
    defineModels,
    models,
    fields,
    onRpc,
    serverState,
    contains,
} from "@web/../tests/web_test_helpers";
import { setupEditor } from "./_helpers/editor";
import { insertText } from "./_helpers/user_actions";

class ResUsers extends models.Model {
    _name = "res.users";
    _records = [
        {
            id: serverState.userId,
        },
    ];
}

class OneModel extends models.Model {
    name = fields.Char({ string: "The many2one model name" });
}

class SomeModel extends models.Model {
    _name = "some.model";

    field = fields.Char({ string: "My little field" });
    many2one_model_id = fields.Many2one({ relation: "one.model" });
}

onRpc("has_group", () => true);
onRpc("mail_allowed_qweb_expressions", () => []);
defineModels([ResUsers, OneModel, SomeModel]);

test("inserted value from dynamic placeholder should contain the data-oe-t-inline attribute", async () => {
    const { editor } = await setupEditor("<p>test[]</p>", {
        config: {
            Plugins: [...MAIN_PLUGINS, ...DYNAMIC_PLACEHOLDER_PLUGINS],
            dynamicPlaceholderResModel: "res.users",
        },
    });
    onRpc("res.users", "mail_get_partner_fields", () => ["partner_id"]);

    await insertText(editor, "/dynamicplaceholder");
    await press("Enter");
    await animationFrame();

    const popover_search_input = document.querySelector(
        ".o_model_field_selector_popover_search .o_input"
    );
    popover_search_input.value = "displayname";
    await manuallyDispatchProgrammaticEvent(popover_search_input, "input", {
        inputType: "insertText",
    });
    await press("Enter");
    await animationFrame();

    const default_value_input = document.querySelector(
        ".o_model_field_selector_default_value_input .o_input"
    );
    await click(default_value_input);
    await manuallyDispatchProgrammaticEvent(default_value_input, "input", {
        inputType: "insertText",
    });
    default_value_input.value = "Test";
    await manuallyDispatchProgrammaticEvent(default_value_input, "input", {
        inputType: "insertText",
    });
    await press("Enter");
    await animationFrame();

    expect("t[data-oe-t-inline]").toHaveCount(1);
});

test("add many2one dynamic placeholder should take the name by default", async () => {
    const { editor, el } = await setupEditor(`<div>[hop hop]</div>`, {
        config: {
            Plugins: [...MAIN_PLUGINS, ...DYNAMIC_PLACEHOLDER_PLUGINS],
            dynamicPlaceholderResModel: "some.model",
        },
    });
    await insertText(editor, "/");
    await contains(".o-we-powerbox .o-we-command-name:contains(/^Dynamic Placeholder$/)").click();

    await contains(
        ".o_model_field_selector_popover_page li[data-name='many2one_model_id'] button"
    ).click();
    expect(queryFirst(".o_model_field_selector_popover span")).toHaveText("Many2one model");

    await contains(".o_model_field_selector_popover button.btn-primary").click();
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
        <p data-selection-placeholder=""><br></p>
            <div class="o-paragraph">
                <t t-out="object.many2one_model_id.display_name" data-oe-t-inline="true" data-oe-protected="true" contenteditable="false"></t>[]
            </div>
        <p data-selection-placeholder=""><br></p>
    `)
    );
});
