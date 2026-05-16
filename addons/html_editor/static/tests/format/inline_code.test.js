import { animationFrame, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "../_helpers/editor";
import { deleteBackward, deleteForward, insertText } from "../_helpers/user_actions";
import { getContent } from "../_helpers/selection";
import { contains } from "@web/../tests/web_test_helpers";
import { expectElementCount } from "../_helpers/ui_expectations";
import { click } from "@odoo/hoot-dom";
import { expandToolbar } from "../_helpers/toolbar";

test("should merge successive inline code", async () => {
    await testEditor({
        contentBefore: `<p><code class="o_inline_code">first</code></p>[]<p><code class="o_inline_code">second</code></p>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
        },
        contentAfter: `<p><code class="o_inline_code">first[]second</code></p>`,
    });
});

test("should remove empty inline code (backspace)", async () => {
    await testEditor({
        contentBefore: `<p>abc<code class="o_inline_code">x[]</code>def</p>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
        },
        contentAfter: `<p>abc[]def</p>`,
    });
});

test("should remove empty inline code (delete)", async () => {
    await testEditor({
        contentBefore: `<p>abc<code class="o_inline_code">[]x</code>def</p>`,
        stepFunction: async (editor) => {
            deleteForward(editor);
        },
        contentAfter: `<p>abc[]def</p>`,
    });
});

test("should remove empty inline code from start of list entry", async () => {
    await testEditor({
        contentBefore: `<ul><li><code class="o_inline_code">x</code></li><li><code class="o_inline_code">y</code>[]abc</li></ul>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
        },
        contentAfter: `<ul><li><code class="o_inline_code">x</code></li><li>[]abc</li></ul>`,
    });
});

test("should create inline code and exclude surrounding formatting", async () => {
    await testEditor({
        contentBefore: "<p><strong><em><u>a`bcd[]ef</u></em></strong></p>",
        stepFunction: async (editor) => {
            await insertText(editor, "`");
        },
        contentAfter: `<p><strong><em><u>a</u></em></strong><code class="o_inline_code">bcd</code>[]<strong><em><u>ef</u></em></strong></p>`,
    });
});

test("should paste external block html as plain text inside inline code", async () => {
    await testEditor({
        contentBefore: `<p>ab<code class="o_inline_code">Inline[]Code</code>cd</p>`,
        stepFunction: async (editor) => {
            const clipboardData = new DataTransfer();
            clipboardData.setData("text/plain", "Titlepara bolda");
            clipboardData.setData(
                "text/html",
                `<h2>Title</h2><p>para <strong>bold</strong></p><ul><li>a</li></ul>`
            );
            const pasteEvent = new ClipboardEvent("paste", {
                clipboardData,
                bubbles: true,
            });
            editor.editable.dispatchEvent(pasteEvent);
        },
        contentAfter: `<p>ab<code class="o_inline_code">InlineTitlepara bolda[]Code</code>cd</p>`,
    });
});

test("should paste Odoo editor html as plain text inside inline code", async () => {
    await testEditor({
        contentBefore: `<p>ab<code class="o_inline_code">Inline[]Code</code>cd</p>`,
        stepFunction: async (editor) => {
            const clipboardData = new DataTransfer();
            clipboardData.setData("text/plain", "Hello Odoo self.env.cr._enable_logging()");
            clipboardData.setData(
                "application/vnd.odoo.odoo-editor",
                `<p class="o_paragraph">Hello <strong>Odoo </strong><a href="http://self.env.cr">self.env.cr</a>._enable_logging()</p>`
            );
            const pasteEvent = new ClipboardEvent("paste", {
                clipboardData,
                bubbles: true,
            });
            editor.editable.dispatchEvent(pasteEvent);
        },
        contentAfter: `<p>ab<code class="o_inline_code">InlineHello Odoo self.env.cr._enable_logging()[]Code</code>cd</p>`,
    });
});

test("should not open powerbox inside inline code", async () => {
    const { editor } = await setupEditor(`<p>abc<code class="o_inline_code">tes[]t</code>def</p>`);
    await insertText(editor, "/");
    await expectElementCount(".o-we-powerbox", 0);
});

test.tags("desktop");
test("should not open toolbar when selection is inside inline code", async () => {
    await setupEditor(`<p>abc<code class="o_inline_code">t[es]t</code>def</p>`);
    await expectElementCount(".o-we-toolbar", 0);
});

test("should open toolbar for mixed selection and apply formatting outside inline code", async () => {
    const { el } = await setupEditor(`<p>abc<code class="o_inline_code">t[est</code>de]f</p>`);

    // Toolbar should be visible as selection is not fully inside inline code.
    await expectElementCount(".o-we-toolbar", 1);
    await expandToolbar();

    // Apply bold should affect only the part outside inline code ("de").
    await click(".o-we-toolbar button[name='bold']");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<code class="o_inline_code">\ufefft[est\ufeff</code>\ufeff<strong>de]</strong>f</p>`
    );

    // Apply text color should still affect only the non-inline-code portion.
    await click(".o-we-toolbar .o-select-color-foreground");
    await expectElementCount(".o_font_color_selector", 1);
    await contains(".btn:contains('Solid')").click();
    await contains(".o_color_button[data-color='#0000FF']").click();
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<code class="o_inline_code">\ufefft[est\ufeff</code>\ufeff<font style="color: rgb(0, 0, 255);"><strong>de]</strong></font>f</p>`
    );
    // Apply font size formatting should wrap only the external text.
    await contains(".o-we-toolbar [name='font_size_selector'].dropdown-toggle").click();
    await contains(`.o_font_size_selector_menu .dropdown-item:contains('80')`).click();
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<code class="o_inline_code">\ufefft[est\ufeff</code>\ufeff<span class="display-1-fs"><font style="color: rgb(0, 0, 255);"><strong>de]</strong></font></span>f</p>`
    );
});
