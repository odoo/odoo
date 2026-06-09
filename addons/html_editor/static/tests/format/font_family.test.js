import { test, expect } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { click, queryOne, waitFor } from "@odoo/hoot-dom";
import { getContent } from "../_helpers/selection";
import { setFontFamily, undo, redo } from "../_helpers/user_actions";
import { execCommand } from "../_helpers/userCommands";
import { animationFrame } from "@odoo/hoot-mock";
import { expandToolbar } from "../_helpers/toolbar";

test("should give a few characters a fontFamily", async () => {
    await testEditor({
        contentBefore: `<p>ab[cde]fg</p>`,
        stepFunction: setFontFamily("testFont"),
        contentAfter: `<p>ab<span style="font-family: testFont;">[cde]</span>fg</p>`,
    });
});

test("should remove the fontFamily from a few characters (set default)", async () => {
    await testEditor({
        contentBefore: `<p><span style="font-family: testFont;">ab[cde]fg</span></p>`,
        stepFunction: setFontFamily(false),
        contentAfter: `<p><span style="font-family: testFont;">ab</span>[cde]<span style="font-family: testFont;">fg</span></p>`,
    });
});

test("should remove the fontFamily from a few characters (remove format)", async () => {
    await testEditor({
        contentBefore: `<p><span style="font-family: testFont;">ab[cde]fg</span></p>`,
        stepFunction: (editor) => execCommand(editor, "removeFormat"),
        contentAfter: `<p><span style="font-family: testFont;">ab</span>[cde]<span style="font-family: testFont;">fg</span></p>`,
    });
});

test("should give two paragraphs a fontFamily", async () => {
    await testEditor({
        contentBefore: "<p>[abc</p><p>def]</p>",
        stepFunction: setFontFamily("testFont"),
        contentAfter: `<p><span style="font-family: testFont;">[abc</span></p><p><span style="font-family: testFont;">def]</span></p>`,
    });
});

test("should remove the fontFamily from two paragraphs", async () => {
    await testEditor({
        contentBefore: `<p><span style="font-family: testFont;">[abc</span></p><p><span style="font-family: testFont;">def]</span></p>`,
        stepFunction: setFontFamily(false),
        contentAfter: `<p>[abc</p><p>def]</p>`,
    });
});

test("should overide fontFamily on the selected characters", async () => {
    await testEditor({
        contentBefore: `<p><span style="font-family: a;">ab[cde]fg</span></p>`,
        stepFunction: setFontFamily("b"),
        contentAfter: `<p><span style="font-family: a;">ab</span><span style="font-family: b;">[cde]</span><span style="font-family: a;">fg</span></p>`,
    });
});

test("should change the font family of a few characters", async () => {
    const { el } = await setupEditor("<p>ab[cde]fg</p>");
    await expandToolbar();
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Default font");
    await click(".btn[name='font_family']");
    await waitFor(".o_font_family_selector_menu");
    await click(".o_font_family_selector_menu .o-dropdown-item:nth-child(2)");
    await animationFrame();
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Arial");
    expect(getContent(el)).toBe(
        '<p>ab<span style="font-family: Arial, sans-serif;">[cde]</span>fg</p>'
    );
});
test("should undo and redo the font family changes", async () => {
    const { editor, el } = await setupEditor("<p>ab[cde]fg</p>");
    await expandToolbar();
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Default font");
    await click(".btn[name='font_family']");
    await waitFor(".o_font_family_selector_menu");
    await click(".o_font_family_selector_menu .o-dropdown-item:nth-child(2)");
    await animationFrame();
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Arial");
    await undo(editor);
    expect(getContent(el)).toBe("<p>ab[cde]fg</p>");
    await redo(editor);
    expect(getContent(el)).toBe(
        '<p>ab<span style="font-family: Arial, sans-serif;">[cde]</span>fg</p>'
    );
});

test("should remove font family on the selected content using remove format", async () => {
    const { el } = await setupEditor(
        '<p>ab<span style="font-family: Arial, sans-serif;">[cde]</span>fg</p>'
    );
    await expandToolbar();
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Arial");
    await click(".btn[title='Remove Format (Ctrl + Space)']");
    await waitFor(".btn[name='font_family']:contains('Default font')");
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Default font");
    expect(getContent(el)).toBe("<p>ab[cde]fg</p>");
});

test("should remove font family on the selected content using Default font family option", async () => {
    const { el } = await setupEditor(
        '<p>ab<span style="font-family: Arial, sans-serif;">[cde]</span>fg</p>'
    );
    await expandToolbar();
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Arial");
    await click(".btn[name='font_family']");
    await waitFor(".o_font_family_selector_menu");
    await click(".o_font_family_selector_menu .o-dropdown-item:first-child");
    await animationFrame();
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Default font");
    expect(getContent(el)).toBe("<p>ab[cde]fg</p>");
});

test("should contain the 5 available font + default", async () => {
    await setupEditor("<p>ab[cde]fg</p>");
    await expandToolbar();
    expect(queryOne(".btn[name='font_family']").textContent).toBe("Default font");
    await click(".btn[name='font_family']");
    await animationFrame();
    await waitFor(".o_font_family_selector_menu");
    const items = document.querySelectorAll(".o_font_family_selector_menu .o-dropdown-item");
    expect(items.length).toBe(6);
    for (let i = 0; i < items.length; i++) {
        expect(items[i].textContent).toBe(
            [
                "Default system font",
                "Arial (sans-serif)",
                "Verdana (sans-serif)",
                "Tahoma (sans-serif)",
                "Trebuchet MS (sans-serif)",
                "Courier New (monospace)",
            ][i]
        );
    }
});

test("should not apply font size directly on a translation wrapper span when fully selected", async () => {
    await testEditor({
        contentBefore:
            '<p><span data-oe-model="ir.ui.view" data-oe-id="1" data-oe-field="arch_db" ' +
            'data-oe-translation-state="translated" ' +
            'data-oe-translation-source-sha="testsha" ' +
            'class="o_editable" contenteditable="true">' +
            '[De ultieme ervaring van verbinding]</span></p>',
        stepFunction: async (editor) => {
            editor.shared.format.formatSelection("setFontSizeClassName", {
                formatProps: { className: "h5-fs" },
                applyStyle: true,
            });
        },
        contentAfter:
            '<p><span data-oe-model="ir.ui.view" data-oe-id="1" data-oe-field="arch_db" ' +
            'data-oe-translation-state="translated" ' +
            'data-oe-translation-source-sha="testsha" ' +
            'class="o_editable" contenteditable="true">' +
            '<span class="h5-fs">[De ultieme ervaring van verbinding]</span></span></p>',
    });
});

test("should not apply a custom font size directly on a translation wrapper span when fully selected", async () => {
    await testEditor({
        contentBefore:
            '<p><span data-oe-model="ir.ui.view" data-oe-id="1" data-oe-field="arch_db" ' +
            'data-oe-translation-state="translated" ' +
            'data-oe-translation-source-sha="testsha" ' +
            'class="o_editable" contenteditable="true">' +
            '[De ultieme ervaring van verbinding]</span></p>',
        stepFunction: async (editor) => {
            editor.shared.format.formatSelection("fontSize", {
                formatProps: { size: "14px" },
                applyStyle: true,
            });
        },
        contentAfter:
            '<p><span data-oe-model="ir.ui.view" data-oe-id="1" data-oe-field="arch_db" ' +
            'data-oe-translation-state="translated" ' +
            'data-oe-translation-source-sha="testsha" ' +
            'class="o_editable" contenteditable="true">' +
            '<span style="font-size: 14px;">[De ultieme ervaring van verbinding]</span></span></p>',
    });
});

test("should still apply font size to an inner span when only part of a translation element is selected", async () => {
    await testEditor({
        contentBefore:
            '<p><span data-oe-model="ir.ui.view" data-oe-id="1" data-oe-field="arch_db" ' +
            'data-oe-translation-state="translated" ' +
            'data-oe-translation-source-sha="testsha" ' +
            'class="o_editable" contenteditable="true">' +
            'De [ultieme] ervaring van verbinding</span></p>',
        stepFunction: async (editor) => {
            editor.shared.format.formatSelection("setFontSizeClassName", {
                formatProps: { className: "h5-fs" },
                applyStyle: true,
            });
        },
        contentAfter:
            '<p><span data-oe-model="ir.ui.view" data-oe-id="1" data-oe-field="arch_db" ' +
            'data-oe-translation-state="translated" ' +
            'data-oe-translation-source-sha="testsha" ' +
            'class="o_editable" contenteditable="true">' +
            'De <span class="h5-fs">[ultieme]</span> ervaring van verbinding</span></p>',
    });
});
