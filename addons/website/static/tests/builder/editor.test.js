import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { click, manuallyDispatchProgrammaticEvent, waitFor, queryOne } from "@odoo/hoot-dom";
import { isTextNode } from "@html_editor/utils/dom_info";
import { parseHTML } from "@html_editor/utils/html";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { expandToolbar } from "@html_editor/../tests/_helpers/toolbar";
import { FontPlugin } from "@html_editor/main/font/font_plugin";

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

test("should set contenteditable to false on .o_not_editable elements", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <div class="o_not_editable">
            <p>abc</p>
        </div>
    `);
    const editor = getEditor();
    const div = editor.editable.querySelector("div.o_not_editable");
    expect(div).toHaveAttribute("contenteditable", "false");

    // Add a snippet-like element
    const snippetHtml = `
        <section class="o_not_editable">
            <p>abc</p>
        </section>
    `;
    const snippet = parseHTML(editor.document, snippetHtml).firstChild;
    div.after(snippet);
    editor.shared.history.addStep();
    // Normalization should set contenteditable to false
    expect(snippet).toHaveAttribute("contenteditable", "false");
});

test("should preserve iframe in the toolbar's font size input", async () => {
    const { getEditor } = await setupWebsiteBuilder(`
        <section class="s_text_block pt40 pb40 o_colored_level" data-snippet="s_text_block" data-name="Text">
            <div class="container s_allow_columns">
                <p>Some text.</p>
                <p>Some more text.</p>
            </div>
        </section>
    `);
    const editor = getEditor();
    const p = editor.editable.querySelector("p");
    const p2 = p.nextElementSibling;
    // Activate the text block snippet.
    click(p);

    // Select the word "more".
    editor.shared.selection.setSelection({
        anchorNode: p2.firstChild,
        anchorOffset: 5,
        focusNode: p2.firstChild,
        focusOffset: 9,
    });
    await waitFor(".o-we-toolbar");
    // Get the font size selector input.
    let iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    let inputEl = iframeEl.contentWindow.document?.querySelector("input");
    // Change the font style from paragraph to paragraph.
    await contains(".o-we-toolbar .btn[name='font'].dropdown-toggle").click();
    await waitFor(".btn[name='font'].dropdown-toggle.show");
    await contains(".dropdown-menu [name='p']").click();
    iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    let newInputEl = iframeEl.contentWindow.document?.querySelector("input");
    expect(newInputEl).toBe(inputEl); // The input shouldn't have been changed.

    // Select the first word "text".
    editor.shared.selection.setSelection({
        anchorNode: p.firstChild,
        anchorOffset: 5,
        focusNode: p.firstChild,
        focusOffset: 9,
    });
    await waitFor(".o-we-toolbar");
    // Get the font size selector input.
    iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    inputEl = iframeEl.contentWindow.document?.querySelector("input");
    // Change the font style from paragraph to header 1.
    await contains(".o-we-toolbar .btn[name='font'].dropdown-toggle").click();
    await waitFor(".btn[name='font'].dropdown-toggle.show");
    await contains(".dropdown-menu [name='h2']").click();
    iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    newInputEl = iframeEl.contentWindow.document?.querySelector("input");
    expect(newInputEl).toBe(inputEl); // The input shouldn't have been changed.
});

describe("toolbar dropdowns", () => {
    const setup = async () => {
        const { getEditor } = await setupWebsiteBuilder(`<p>abc</p>`);
        const editor = getEditor();
        const p = editor.editable.querySelector("p");
        setSelection({ anchorNode: p, anchorOffset: 0, focusOffset: 1 });
        await waitFor(".o-we-toolbar");
        await expandToolbar();
        return { editor, p };
    };

    const focusAndClick = async (selector) => {
        const target = await waitFor(selector);
        manuallyDispatchProgrammaticEvent(target, "mousedown");
        manuallyDispatchProgrammaticEvent(target, "focus");
        await animationFrame();
        // Dropdown menu needs another animation frame to be closed after the
        // toolbar is closed.
        await animationFrame();
        expect(target).toBeVisible();
        manuallyDispatchProgrammaticEvent(target, "mouseup");
        manuallyDispatchProgrammaticEvent(target, "click");
    };

    test("list dropdown should not close on click", async () => {
        const { editor } = await setup();
        click(".o-we-toolbar .btn[name='list_selector']");
        const bulletedListButtonSelector = ".dropdown-menu button[name='bulleted_list']";
        await focusAndClick(bulletedListButtonSelector);
        await animationFrame();
        expect(bulletedListButtonSelector).toBeVisible();
        expect(bulletedListButtonSelector).toHaveClass("active");
        expect(!!editor.editable.querySelector("ul li")).toBe(true);
    });

    test("text alignment dropdown should not close on click", async () => {
        const { p } = await setup();
        click(".o-we-toolbar .btn[name='text_align']");
        const alignCenterButtonSelector = ".dropdown-menu button.fa-align-center";
        await focusAndClick(alignCenterButtonSelector);
        await animationFrame();
        expect(alignCenterButtonSelector).toBeVisible();
        expect(alignCenterButtonSelector).toHaveClass("active");
        expect(p).toHaveStyle("text-align: center");
    });

    test("font style dropdown should close only after click", async () => {
        const { editor } = await setup();
        click(".o-we-toolbar .btn[name='font']");
        await focusAndClick(".dropdown-menu .dropdown-item[name='h2']");
        await animationFrame();
        expect(!!editor.editable.querySelector("h2")).toBe(true);
    });

    test("font size dropdown should close only after click", async () => {
        patchWithCleanup(FontPlugin.prototype, {
            get fontSizeItems() {
                return [{ name: "test", className: "test-font-size" }];
            },
        });
        const { p } = await setup();
        click(".o-we-toolbar .btn[name='font_size_selector']");
        await focusAndClick(".dropdown-menu .dropdown-item");
        await animationFrame();
        expect(p.firstChild).toHaveClass("test-font-size");
    });

    test("font selector dropdown should not have normal as an option", async () => {
        await setup();
        click(".o-we-toolbar .btn[name='font']");
        await animationFrame();
        expect(".o_font_selector_menu .o-dropdown-item[name='div']").toHaveCount(0);
    });
});
