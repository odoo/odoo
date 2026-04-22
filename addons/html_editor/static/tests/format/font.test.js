import { waitFor } from "@odoo/hoot-dom";
import { setupEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { describe, expect, hover, test, click } from "@odoo/hoot";
import { expandToolbar } from "../_helpers/toolbar";
import { contains } from "@web/../tests/web_test_helpers";

test("should change the containing block with the font", async () => {
    const { el } = await setupEditor("<p>ab[cde]fg</p>");
    await waitFor(".btn[name='font_type']");
    expect(".btn[name='font_type']").toHaveText("Paragraph");
    await contains(".btn[name='font_type']").click();
    await waitFor(".o_font_type_selector_menu");
    await contains(".o_font_type_selector_menu .o-dropdown-item[name=blockquote]").click();
    expect(".btn[name='font_type']").toHaveText("Quote");
    expect(getContent(el)).toBe("<blockquote>ab[cde]fg</blockquote>");
});

test("should have font tool only if the block is content editable", async () => {
    for (const [contenteditable, count] of [
        [false, 0],
        [true, 1],
    ]) {
        await setupEditor(
            `<div contenteditable="${contenteditable}"><p><span contenteditable="true">ab[cde]fg</span></p></div>`
        );
        await expandToolbar();
        expect(".btn[name='font_type']").toHaveCount(count);
    }
});

describe("Font type preview", () => {
    test.tags("desktop");
    test("should preview different font type on hover", async () => {
        const { el } = await setupEditor("<p>a[bc]d</p>");
        await waitFor(".btn[name='font_type']");
        expect(".btn[name='font_type']").toHaveText("Paragraph");
        await contains(".btn[name='font_type']").click();
        await waitFor(".o_font_type_selector_menu");
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='h1']");
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='h2']");
        expect(getContent(el)).toBe(`<h2>a[bc]d</h2>`);
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='h3']");
        expect(getContent(el)).toBe(`<h3>a[bc]d</h3>`);
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='div']");
        expect(getContent(el)).toBe(`<div class="o-paragraph">a[bc]d</div>`);
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='p']");
        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='blockquote']");
        expect(getContent(el)).toBe(`<blockquote>a[bc]d</blockquote>`);
    });

    test.tags("desktop");
    test("should revert preview to original type when mouse leaves without applying font family style", async () => {
        const { el } = await setupEditor("<p>a[bc]d</p>");
        await waitFor(".btn[name='font_type']");
        expect(".btn[name='font_type']").toHaveText("Paragraph");
        await contains(".btn[name='font_type']").click();
        await waitFor(".o_font_type_selector_menu");
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='h1']");
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);
        await hover(el);
        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='h1']");
        await click(".o_font_type_selector_menu .o-dropdown-item[name='h1']");
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);
        await hover(".o_font_type_selector_menu .o-dropdown-item[name='p']");
        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);
        await hover(el);
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);
    });
});
