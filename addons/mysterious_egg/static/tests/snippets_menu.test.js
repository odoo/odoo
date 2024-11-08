import { setContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { animationFrame, click } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, openSnippetsMenu, setupWebsiteBuilder } from "./helpers";

defineWebsiteModels();

test("open SnippetsMenu and discard", async () => {
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openSnippetsMenu();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(0);
    await click(".o-snippets-top-actions button:contains(Discard)");
    await animationFrame();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
});

test("undo and redo buttons", async () => {
    const { getEditor } = await setupWebsiteBuilder("<p> Text </p>");
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openSnippetsMenu();
    const editor = getEditor();
    setContent(editor.editable, "<p> Text[] </p>");
    editor.dispatch("ADD_STEP");
    await insertText(editor, "a");
    expect(editor.editable).toHaveInnerHTML("<p> Texta </p>");
    await animationFrame();
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(editor.editable).toHaveInnerHTML("<p> Text </p>");
    await click(".o-snippets-menu button.fa-repeat");
    expect(editor.editable).toHaveInnerHTML("<p> Texta </p>");
});

test("drag and drop snippet inner content", async () => {
    const { getEditor } = await setupWebsiteBuilder("<div><p>Text</p></div>");
    await openSnippetsMenu();
    const editor = getEditor();
    expect(editor.editable).toHaveInnerHTML(`<div><p>Text</p></div>`);

    const { moveTo, drop } = await contains(".o-website-snippetsmenu [name='Button']").drag();
    expect(editor.editable).toHaveInnerHTML(
        `<div><div class="oe_drop_zone oe_insert"></div><p>Text</p><div class="oe_drop_zone oe_insert"></div></div>`
    );

    await moveTo(editor.editable.querySelector(".oe_drop_zone"));
    expect(editor.editable).toHaveInnerHTML(
        `<div><div class="oe_drop_zone oe_insert o_dropzone_highlighted"></div><p>Text</p><div class="oe_drop_zone oe_insert"></div></div>`
    );

    await drop(editor.editable.querySelector(".oe_drop_zone"));
    expect(editor.editable).toHaveInnerHTML(
        `<div>\ufeff<a class="btn btn-primary o_snippet_drop_in_only" href="#" data-snippet="s_button">\ufeffButton\ufeff</a>\ufeff<p>Text</p></div>`
    );
});
