import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { click, manuallyDispatchProgrammaticEvent, press } from "@odoo/hoot-dom";
import { DYNAMIC_PLACEHOLDER_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { defineModels, models, onRpc, serverState } from "@web/../tests/web_test_helpers";
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

onRpc("has_group", () => true);
onRpc("mail_allowed_qweb_expressions", () => []);
defineModels([ResUsers]);

test("inserted value from dynamic placeholder should contain the data-oe-t-inline attribute", async () => {
    const { editor } = await setupEditor("<p>test[]</p>", {
        config: {
            Plugins: [...MAIN_PLUGINS, ...DYNAMIC_PLACEHOLDER_PLUGINS],
            dynamicPlaceholderResModel: "res.users",
        },
    });

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
