import { expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";
import { setupEditor, testEditor } from "./_helpers/editor";
import { fixInvalidHTML } from "@html_editor/utils/sanitize";

const Markup = markup().constructor;

test("sanitize should remove nasty elements", async () => {
    const { editor } = await setupEditor("");
    expect(editor.shared.sanitize.sanitize("<img src=x onerror=alert(1)//>")).toBe('<img src="x">');
    expect(editor.shared.sanitize.sanitize("<svg><g/onload=alert(2)//<p>")).toBe(
        "<svg><g></g></svg>"
    );
    expect(
        editor.shared.sanitize.sanitize("<p>abc<iframe//src=jAva&Tab;script:alert(3)>def</p>")
    ).toBe("<p>abc</p>");
});

test("sanitize should leave t-field, t-out, t-esc as is", async () => {
    const { editor } = await setupEditor("");
    expect(editor.shared.sanitize.sanitize(`<span t-esc="expr"></span>`)).toBe(
        '<span t-esc="expr"></span>'
    );
    expect(editor.shared.sanitize.sanitize(`<span t-out="expr"></span>`)).toBe(
        '<span t-out="expr"></span>'
    );
    expect(editor.shared.sanitize.sanitize(`<span t-field="expr"></span>`)).toBe(
        '<span t-field="expr"></span>'
    );
});

test("sanitize plugin should handle contenteditable attribute with o-contenteditable-[true/false] class", async () => {
    await testEditor({
        contentBefore: `<p class="o-contenteditable-true">a[]</p><p class="o-contenteditable-false">b</p>`,
        contentAfterEdit: `<p class="o-contenteditable-true" contenteditable="true">a[]</p><p class="o-contenteditable-false" contenteditable="false">b</p><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`,
        contentAfter: `<p class="o-contenteditable-true">a[]</p><p class="o-contenteditable-false">b</p>`,
    });
});

test("sanitize plugin should handle role attribute with data-oe-role attribute", async () => {
    await testEditor({
        contentBefore: `<p data-oe-role="status">a[]</p>`,
        contentAfterEdit: `<p data-oe-role="status" role="status">a[]</p>`,
        contentAfter: `<p data-oe-role="status">a[]</p>`,
    });
});

test("sanitize plugin should handle aria-label attribute with data-oe-aria-label attribute", async () => {
    await testEditor({
        contentBefore: `<p data-oe-aria-label="status">a[]</p>`,
        contentAfterEdit: `<p data-oe-aria-label="status" aria-label="status">a[]</p>`,
        contentAfter: `<p data-oe-aria-label="status">a[]</p>`,
    });
});

test("fixInvalidHTML should close self-closing elements", () => {
    expect(fixInvalidHTML(markup`<t/>`).toString()).toBe("<t></t>");
    expect(fixInvalidHTML(markup`<t class="test"/>`).toString()).toBe('<t class="test"></t>');
    expect(fixInvalidHTML(markup`<a/>`).toString()).toBe("<a></a>");
    expect(fixInvalidHTML(markup`<a href="#"/>`).toString()).toBe('<a href="#"></a>');
    expect(fixInvalidHTML(markup`<strong/>`).toString()).toBe("<strong></strong>");
    expect(fixInvalidHTML(markup`<strong class="bold"/>`).toString()).toBe(
        '<strong class="bold"></strong>'
    );
    expect(fixInvalidHTML(markup`<span/>`).toString()).toBe("<span></span>");
    expect(fixInvalidHTML(markup`<span id="test"/>`).toString()).toBe('<span id="test"></span>');
    expect(
        fixInvalidHTML(
            markup`<t t-out="object.name"/>asdf<t t-out="object.parner_id.name"/>`
        ).toString()
    ).toBe('<t t-out="object.name"></t>asdf<t t-out="object.parner_id.name"></t>');
});

test("fixInvalidHTML escapes string input", () => {
    expect(fixInvalidHTML("<t/>").toString()).toBe("&lt;t/&gt;");
    expect(fixInvalidHTML('<a href="?param=value&other=test"/>').toString()).toBe(
        "&lt;a href=&quot;?param=value&amp;other=test&quot;/&gt;"
    );
});

test("fixInvalidHTML should return markup", () => {
    expect(fixInvalidHTML(markup`<t/>`)).toBeInstanceOf(Markup);
    expect(fixInvalidHTML("<t/>")).toBeInstanceOf(Markup);
});

test("fixInvalidHTML handles nested self-closing tags correctly", () => {
    expect(fixInvalidHTML(markup`<t><t/><t><t/></t></t>`).toString()).toBe(
        "<t><t></t><t><t></t></t></t>"
    );
    expect(fixInvalidHTML(markup`<span><span class="inner"/></span>`).toString()).toBe(
        '<span><span class="inner"></span></span>'
    );
});

test("fixInvalidHTML preserves escaped content in attributes and text", () => {
    expect(fixInvalidHTML(markup`<span title="quoted &amp; special"/>`).toString()).toBe(
        `<span title="quoted &amp; special"></span>`
    );
    expect(fixInvalidHTML(markup`<p>Text with &lt;escaped&gt; content</p>`).toString()).toBe(
        `<p>Text with &lt;escaped&gt; content</p>`
    );
});

test("fixInvalidHTML attribute", () => {
    // Properly quoted attributes should work
    expect(fixInvalidHTML(markup`<t onclick="alert('test')"/>`).toString()).toBe(
        `<t onclick="alert('test')"></t>`
    );

    // Unclosed quotes should NOT be converted (security protection)
    expect(fixInvalidHTML(markup`<t class="unclosed/>`).toString()).toBe(`<t class="unclosed/>`);

    // Mismatched quotes should NOT be converted (security protection)
    expect(fixInvalidHTML(markup`<t class="test'/>`).toString()).toBe(`<t class="test'/>`);

    // Valid data attributes with special characters should work
    expect(fixInvalidHTML(markup`<span data-config='{"key": "value"}'/>`).toString()).toBe(
        `<span data-config='{"key": "value"}'></span>`
    );

    // Attributes with invalid characters in unquoted values should NOT match
    expect(fixInvalidHTML(markup`<t class=test>value/>`).toString()).toBe(`<t class=test>value/>`);

    // Attributes containing < or > characters in quoted values should work
    expect(fixInvalidHTML(markup`<t data-rule="value < 10"/>`).toString()).toBe(
        `<t data-rule="value < 10"></t>`
    );
    expect(fixInvalidHTML(markup`<span title="score > 100"/>`).toString()).toBe(
        `<span title="score > 100"></span>`
    );
});
