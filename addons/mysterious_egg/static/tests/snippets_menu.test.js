import { expect, test } from "@odoo/hoot";
import { defineWebsiteModels, openSnippetsMenu, setupWebsiteBuilder } from "./helpers";
import { animationFrame, click } from "@odoo/hoot-dom";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { setContent } from "@html_editor/../tests/_helpers/selection";

defineWebsiteModels();

test("open SnippetsMenu and discard", async () => {
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    await animationFrame();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openSnippetsMenu();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(0);
    await click(".o-snippets-top-actions button:contains(Discard)");
    await animationFrame();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
});

test("undo and redo buttons", async () => {
    const { getEditor } = await setupWebsiteBuilder("<p> Text </p>");
    await animationFrame();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openSnippetsMenu();
    const editor = getEditor();
    setContent(editor.editable, "<p> Text[] </p>");
    await insertText(editor, "a");
    expect(editor.editable.innerHTML).toBe("<p> Texta </p>");
    await animationFrame();
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(editor.editable.innerHTML).toBe("<p> Text </p>");
    await click(".o-snippets-menu button.fa-repeat");
    expect(editor.editable.innerHTML).toBe("<p> Texta </p>");
});
