import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { manuallyDispatchProgrammaticEvent } from "@odoo/hoot-dom";
import { isTextNode } from "@html_editor/utils/dom_info";

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
    expect(p).toHaveInnerHTML(`x<span class="fa fa-heart" contenteditable="false">\u200b</span>`);
});

test("should delete text forward", async () => {
    const keyPress = async (editor, key) => {
        await manuallyDispatchProgrammaticEvent(editor.editable, "keydown", { key });
        await manuallyDispatchProgrammaticEvent(editor.editable, "keyup", { key });
    };
    const { getEditor } = await setupWebsiteBuilder(`<p>abc</p><p>def</p>`);
    const editor = getEditor();
    const p = editor.editable.querySelector("p");
    editor.shared.selection.setSelection({ anchorNode: p, anchorOffset: 1 });
    await keyPress(editor, "delete");
    // paragraphs get merged
    expect(p).toHaveInnerHTML("abcdef");
    await keyPress(editor, "delete");
    // following character gets deleted
    expect(p).toHaveInnerHTML("abcef");
});

test("unsplittable node predicates should not crash when called with text node argument", async () => {
    const { getEditor } = await setupWebsiteBuilder(`<p>abc</p>`);
    const editor = getEditor();
    const textNode = editor.editable.querySelector("p").firstChild;
    expect(isTextNode(textNode)).toBe(true);
    expect(() =>
        editor.resources.unsplittable_node_predicates.forEach((p) => p(textNode))
    ).not.toThrow();
});
