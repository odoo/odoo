import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./helpers";

defineWebsiteModels();

test("should add an icon from the media modal dialog", async () => {
    const { getEditor } = await setupWebsiteBuilder(`<p>x</p>`);
    const editor = getEditor();
    const p = editor.document.querySelector("p");
    editor.shared.selection.focusEditable();
    editor.shared.selection.setSelection({
        anchorNode: p,
        anchorOffset: 1,
        focusNode: p,
        focusOffset: 1,
    });
    await insertText(editor, "/image");
    await animationFrame();
    await contains(".o-we-command").click();
    await contains(".modal .modal-body .nav-item:nth-child(3) a").click();
    await contains(".modal .modal-body .fa-heart").click();
    expect(p).toHaveInnerHTML(`x<span class="fa fa-heart" contenteditable="false">​</span>`);
});
