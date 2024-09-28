import { expect, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, press, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";

test("should insert a banner with focus inside followed by a paragraph", async () => {
    const { el, editor } = await setupEditor("<p>Test[]</p>");
    await insertText(editor, "/banner");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Banner Info");

    await press("enter");
    expect(getContent(el)).toBe(
        `<p>Test</p><div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">
                    <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                </div>
            </div><p><br></p>`
    );

    await insertText(editor, "/");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);

    await insertText(editor, "banner");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(0, {
        message: "shouldn't be possible to add a banner inside a banner",
    });
});

test("press 'ctrl+a' inside a banner should select all the banner content", async () => {
    const { el, editor } = await setupEditor("<p>Test[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    await insertText(editor, "Test1");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "Test2");
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        `<p>Test</p><div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">[
                    <p>Test1</p><p>Test2<br></p>
                ]</div>
            </div><p><br></p>`
    );
});

test("remove all content should preserves the first paragraph tag inside the banner", async () => {
    const { el, editor } = await setupEditor("<p>Test[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    await insertText(editor, "Test1");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "Test2");
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        `<p>Test</p><div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">[
                    <p>Test1</p><p>Test2<br></p>
                ]</div>
            </div><p><br></p>`
    );

    await press("Backspace");
    expect(getContent(el)).toBe(
        `<p>Test</p><div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true"><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p></div>
            </div><p><br></p>`
    );
});

test("Everything gets selected with ctrl+a, including a contenteditable=false as first element", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    // Move the selection outside of the banner
    setSelection({ anchorNode: el.querySelectorAll("p")[1], anchorOffset: 0 });
    await insertText(editor, "Test1");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "Test2");
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        `[\u200b<div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">
                    <p><br></p>
                </div>
            </div><p>Test1</p><p>Test2<br></p>]`,
        { message: "should select everything" }
    );

    await press("Backspace");
    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("Everything gets selected with ctrl+a, including a contenteditable=false as first two elements", async () => {
    const { el } = await setupEditor(
        '<div contenteditable="false">a</div><div contenteditable="false">b</div><p>cd[]</p>'
    );
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        '[<div contenteditable="false">a</div><div contenteditable="false">b</div><p>cd</p>]'
    );

    await press("Backspace");
    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("Can change an emoji banner", async () => {
    const { editor } = await setupEditor("<p>Test[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    expect("i.o_editor_banner_icon").toHaveText("💡");
    await click("i.o_editor_banner_icon");
    await waitFor(".o-EmojiPicker", { timeout: 500 });
    await click(".o-EmojiPicker .o-Emoji");
    await animationFrame();
    expect("i.o_editor_banner_icon").toHaveText("😀");
    editor.dispatch("HISTORY_UNDO");
    expect("i.o_editor_banner_icon").toHaveText("💡");
    editor.dispatch("HISTORY_REDO");
    expect("i.o_editor_banner_icon").toHaveText("😀");
});

test("add banner inside empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>[]<br></li></ul>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    expect(getContent(el)).toBe(
        `<ul><li><br><div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">
                    <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                </div>
            </div><br></li></ul>`
    );
});

test("add banner inside non-empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>Test[]</li></ul>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    expect(getContent(el)).toBe(
        `<ul><li>Test<div class="o_editor_banner user-select-none o_not_editable lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" role="status" contenteditable="false">
                <i class="o_editor_banner_icon mb-3 fst-normal" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">
                    <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                </div>
            </div><br></li></ul>`
    );
});
