import { BuilderActionsPlugin } from "@html_builder/core/builder_actions_plugin";
import { OperationPlugin } from "@html_builder/core/operation_plugin";
import { setupEditor } from "@html_editor/../tests/_helpers/editor";
import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { CustomizeMailingPlugin } from "@mass_mailing/builder/plugins/customize_mailing_plugin";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";

defineMailModels();

const config = {
    includePlugins: [BuilderActionsPlugin, OperationPlugin, CustomizeMailingPlugin],
};
const customizeMailing = (editor, variable, value) => {
    const actionId = "mass_mailing.CustomizeMailingVariable";
    const builderActions = editor.shared.builderActions;
    return value
        ? builderActions.applyAction(actionId, { params: { variable }, value })
        : builderActions.getAction(actionId).clean({ params: { variable } })
};

test("undo/redo mailing design font sizes", async () => {
    const { editor, el } = await setupEditor(
        `<div class="o_layout"><div class="o_mail_wrapper">
            <div class="o_mail_wrapper_td"><p>Mailing text</p></div>
        </div></div>`,
        { config, props: { iframe: true } }
    );
    const p = el.querySelector(".o_layout p");

    // Change font size to 18px.
    await customizeMailing(editor, "--text-font-size", "18px");
    expect(p).toHaveStyle({ fontSize: "18px" });
    // Change font size to 24px.
    await customizeMailing(editor, "--text-font-size", "24px");
    expect(p).toHaveStyle({ fontSize: "24px" });

    // Undo -> Back to 18px.
    undo(editor);
    await animationFrame();
    expect(p).toHaveStyle({ fontSize: "18px" });

    // Redo -> Back to 24px.
    redo(editor);
    await animationFrame();
    expect(p).toHaveStyle({ fontSize: "24px" });
    expect(editor.getElContent().querySelector("#design-element").textContent).toInclude(
        "--text-font-size: 24px"
    );
});

test("undo/redo mailing design formatting (toggle)", async () => {
    const { editor, el } = await setupEditor(
        `<div class="o_layout"><div class="o_mail_wrapper">
            <div class="o_mail_wrapper_td"><p><a href="/">Mailing link</a></p></div>
        </div></div>`,
        { config, props: { iframe: true } }
    );
    const a = el.querySelector("a");

    // Change link style to italic.
    await customizeMailing(editor, "--link-font-style", "italic");
    expect(a).toHaveStyle({ fontStyle: "italic" });

    // Remove link style.
    customizeMailing(editor, "--link-font-style");
    editor.shared.history.commit();
    expect(a).toHaveStyle({ fontStyle: "normal" });

    // Undo -> back to italic.
    undo(editor);
    await animationFrame();
    expect(a).toHaveStyle({ fontStyle: "italic" });

    // Redo -> back to normal.
    redo(editor);
    await animationFrame();
    expect(a).toHaveStyle({ fontStyle: "normal" });
});
