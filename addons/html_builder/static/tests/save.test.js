import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, openSnippetsMenu, setupWebsiteBuilder, getEditable } from "./helpers";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { setContent } from "@html_editor/../tests/_helpers/selection";
import { onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { click, animationFrame } from "@odoo/hoot-dom";

defineWebsiteModels();

test("basic save", async () => {
    const viewResult = await setupBuilderAndModifyText();
    await click(".o-snippets-top-actions button:contains(Save)");
    expect(viewResult.length).toBe(1);
    expect(viewResult[0]).toBe(
        '<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"><h1 class="title">Hello1</h1></div>'
    );
    await animationFrame();
    expect.verifySteps(["window_reload"]);
});

test("nothing to save", async () => {
    const viewResult = await setupBuilderAndModifyText();
    await animationFrame();
    await click(".o-snippets-menu button.fa-undo");
    await click(".o-snippets-top-actions button:contains(Save)");
    expect(viewResult.length).toBe(0);
    await animationFrame();
    expect.verifySteps(["window_reload"]);
});

async function setupBuilderAndModifyText() {
    const result = [];
    onRpc("ir.ui.view", "save", ({ args }) => {
        result.push(args[1]);
        return true;
    });
    patchWithCleanup(browser.location, {
        reload: function () {
            expect.step("window_reload");
        },
    });
    const { getEditor } = await setupWebsiteBuilder(getEditable('<h1 class="title">Hello</h1>'));
    await openSnippetsMenu();
    expect(":iframe #wrap").toHaveClass("o_editable");
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    const editor = getEditor();
    setContent(editor.editable, getEditable('<h1 class="title">Hello[]</h1>'));
    await insertText(editor, "1");
    expect(":iframe #wrap").toHaveClass("o_dirty");
    return result;
}
