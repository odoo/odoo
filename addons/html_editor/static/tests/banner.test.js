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
            `<p>Test</p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                    </div>
                </div><p><br></p>`
        )
    );

    await insertText(editor, "/");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);

    await insertText(editor, "banner");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 0);

});

test("should insert a banner with DIV as basecontainer and focus inside it", async () => {
    const { el, editor } = await setupEditor("<div>Test[]</div>", {
        config: { baseContainer: "DIV" },
    });
    await insertText(editor, "/banner");
    await animationFrame();
    expect(".active .o-we-command-name").toHaveText("Banner Info");

    await press("enter");
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<div class="o-paragraph">Test</div>
            <div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                    <div class="o-paragraph o-we-hint" placeholder='Type "/" for commands'>[]<br></div>
                </div>
            </div>
            <div class="o-paragraph"><br></div>`
        )
    );
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
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p>Test</p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p>[Test1</p><p>Test2]<br></p>
                    </div>
                </div><p><br></p>`
        )
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
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p>Test</p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p>[Test1</p><p>Test2]<br></p>
                    </div>
                </div><p><br></p>`
        )
    );

    await press("Backspace");
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p>Test</p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true"><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p></div>
                </div><p><br></p>`
        )
    );
});

test("Inserting a banner at the top of the editable also inserts a paragraph above it", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<p><br></p>
            <div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                    <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                </div>
            </div>
            <p><br></p>`
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
            </div><p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
    await press(["ctrl", "a"]);
    await animationFrame();
    expect(getContent(el)).toBe(
        `[<div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="w-100 px-3" contenteditable="true">
                    <p><br></p>
                </div>
            </div><p placeholder='Type "/" for commands' class="o-we-hint">]<br></p>`
    );
});

test("Everything gets selected with ctrl+a, including a banner", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
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
        `<p>[<br></p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                    <p><br></p>
                </div>
            </div><p>Test1</p><p>Test2]<br></p>`,
        { message: "should select everything" }
    );

    await press("Backspace");
    expect(getContent(el)).toBe(
        `<p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("Everything gets selected with ctrl+a, including a contenteditable=false as first two elements", async () => {
    const { el } = await setupEditor(
        '<div data-oe-role="status" contenteditable="false" role="status">a</div><div data-oe-role="status" contenteditable="false" role="status">b</div><p>cd[]</p>'
    );
    await press(["ctrl", "a"]);
    expect(getContent(el)).toBe(
        '[<div data-oe-role="status" contenteditable="false" role="status">a</div><div data-oe-role="status" contenteditable="false" role="status">b</div><p>cd]</p>'
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

test("add banner inside empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>[]<br></li></ul>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<ul><li><br><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                    </div>
                </div><br></li></ul>`
        )
    );
});

test("add banner inside non-empty list", async () => {
    const { el, editor } = await setupEditor("<ul><li>Test[]</li></ul>");
    await insertText(editor, "/bannerinfo");
    await press("enter");
    expect(unformat(getContent(el))).toBe(
        unformat(
            `<ul><li>Test<div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p placeholder='Type "/" for commands' class="o-we-hint">[]<br></p>
                    </div>
                </div><br></li></ul>`
        )
    );
});
