import { expect, test } from "@odoo/hoot";
import { click, manuallyDispatchProgrammaticEvent, press, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { setupEditor } from "./_helpers/editor";
import { getContent, setSelection } from "./_helpers/selection";
import { insertText } from "./_helpers/user_actions";
import { loader } from "@web/core/emoji_picker/emoji_picker";
import { execCommand } from "./_helpers/userCommands";
import { unformat } from "./_helpers/format";
import { expectElementCount } from "./_helpers/ui_expectations";

test("should insert a banner with focus inside followed by a paragraph", async () => {
    const { el, editor } = await setupEditor("<p>Test[]</p>");
    await insertText(editor, "/banner");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Banner Info");

    await press("enter");
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p>Test[]</p>
                    </div>
                </div><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );

    await insertText(editor, "/");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);

    await insertText(editor, "banner");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);
});

test("press 'ctrl+a' inside a banner should select all the banner content", async () => {
    const { el, editor } = await setupEditor("<p>Test[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "Test1");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "Test2");
    await press(["ctrl", "a"]);
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p>[Test</p><p>Test1</p><p>Test2]</p>
                    </div>
                </div><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );
});

test("remove all content should preserve the first paragraph tag inside the banner", async () => {
    const { el, editor } = await setupEditor("<p>Test[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "Test1");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "Test2");
    await press(["ctrl", "a"]);
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p>[Test</p><p>Test1</p><p>Test2]</p>
                    </div>
                </div><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );

    await press("Backspace");
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true"><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p></div>
                </div><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );
});

test("Inserting a banner at the top of the editable also inserts a paragraph above it", async () => {
    const { el, editor } = await setupEditor("<p>test[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p>
            <div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                    <p>test[]</p>
                </div>
            </div>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );
});

test("Everything gets selected with ctrl+a, including a contenteditable=false as first element", async () => {
    const { el } = await setupEditor(
        `<div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">
                    <p><br></p>
                </div>
            </div><p>[]<br></p>`
    );
    await press(["ctrl", "a"]);
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder="">[<br></p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">
                    <p><br></p>
                </div>
            </div><p>]<br></p>`
    );
});

test("Everything gets selected with ctrl+a, including a banner", async () => {
    const { el, editor } = await setupEditor("<p>test[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    // Move the selection outside of the banner
    setSelection({ anchorNode: el.querySelectorAll("p")[2], anchorOffset: 0 });
    await insertText(editor, "Test1");
    await manuallyDispatchProgrammaticEvent(editor.editable, "beforeinput", {
        inputType: "insertParagraph",
    });
    await insertText(editor, "Test2");
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder="">[<br></p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                    <p>test</p>
                </div>
            </div><p>Test1</p><p>Test2]</p>`,
        { message: "should select everything" }
    );
    await press("Backspace");
    expect(getContent(el)).toBe(
        `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("Everything gets selected with ctrl+a, including a contenteditable=false as first two elements", async () => {
    const { el } = await setupEditor(
        '<div data-oe-role="status" contenteditable="false" role="status">a</div><div data-oe-role="status" contenteditable="false" role="status">b</div><p>cd[]</p>'
    );
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        '<p data-selection-placeholder="">[<br></p><div data-oe-role="status" contenteditable="false" role="status">a</div><p data-selection-placeholder=""><br></p><div data-oe-role="status" contenteditable="false" role="status">b</div><p>cd]</p>'
    );

    await press("Backspace");
    expect(getContent(el)).toBe(
        `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("Can change an emoji banner", async () => {
    const { editor } = await setupEditor("<p>Test[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    expect("i.o_editor_banner_icon").toHaveText("💡");
    await loader.loadEmoji();
    await click("i.o_editor_banner_icon");
    await waitFor(".o-EmojiPicker");
    await click(".o-EmojiPicker .o-Emoji");
    await animationFrame();
    expect("i.o_editor_banner_icon").toHaveText("😀");
    execCommand(editor, "historyUndo");
    expect("i.o_editor_banner_icon").toHaveText("💡");
    execCommand(editor, "historyRedo");
    expect("i.o_editor_banner_icon").toHaveText("😀");
});

test("toolbar should be closed when you open the emojipicker", async () => {
    const { editor, el } = await setupEditor(`<p class="test">Test</p><p>a[]</p>`);
    await insertText(editor, "/bannerinfo");
    await press("enter");

    // Move the selection to open the toolbar
    const textNode = el.querySelector(".test").childNodes[0];
    setSelection({ anchorNode: textNode, anchorOffset: 0, focusNode: textNode, focusOffset: 2 });
    await waitFor(".o-we-toolbar");

    await loader.loadEmoji();
    await click("i.o_editor_banner_icon");
    await waitFor(".o-EmojiPicker");
    await animationFrame();
    await expectElementCount(".o-EmojiPicker", 1);
    await expectElementCount(".o-we-toolbar", 0);
});

test.tags("desktop", "iframe");
test("toolbar should be closed when you open the emojipicker (iframe)", async () => {
    const { editor, el } = await setupEditor(`<p class="test">Test</p><p>a[]</p>`, {
        props: { iframe: true },
    });
    await insertText(editor, "/bannerinfo");
    await press("enter");

    // Move the selection to open the toolbar
    const textNode = el.querySelector(".test").childNodes[0];
    setSelection({ anchorNode: textNode, anchorOffset: 0, focusNode: textNode, focusOffset: 2 });
    await waitFor(".o-we-toolbar");

    await loader.loadEmoji();
    await click(":iframe i.o_editor_banner_icon");
    await waitFor(".o-EmojiPicker");
    await animationFrame();
    await expectElementCount(".o-EmojiPicker", 1);
    await expectElementCount(".o-we-toolbar", 0);
});

test("add banner inside empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>[]<br></li></ul>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    await animationFrame();
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<ul><li><br><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>
                    </div>
                </div></li></ul>`
        )
    );
});

test("add banner inside non-empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>Test[]</li></ul>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    await animationFrame();
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<ul><li><br><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p>Test[]</p>
                    </div>
                </div></li></ul>`
        )
    );
});

test("should move heading element inside the banner, with paragraph element after the banner", async () => {
    const { el, editor } = await setupEditor("<h1>Test[]</h1>");
    await insertText(editor, "/banner");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Banner Info");

    await press("enter");
    expect(getContent(el)).toBe(
        `<p data-selection-placeholder=""><br></p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                    <h1>Test[]</h1>
                </div>
            </div><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
    );
});
