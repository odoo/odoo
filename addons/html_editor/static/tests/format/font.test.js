import { animationFrame, press, queryAll, waitFor } from "@odoo/hoot-dom";
import { setupEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { describe, expect, hover, test } from "@odoo/hoot";
import { expandToolbar } from "../_helpers/toolbar";
import { contains } from "@web/../tests/web_test_helpers";

async function setupFontTypeDropdown(content) {
    const { el } = await setupEditor(content);

    await waitFor(".btn[name='font_type']");
    await contains(".btn[name='font_type']").click();
    await waitFor(".o_font_type_selector_menu");

    return { el };
}

function getFontTypeItem(label) {
    return queryAll(".o_font_type_selector_menu .o-dropdown-item").find(
        (el) => el.textContent.trim() === label
    );
}

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

describe("Font type preview with mouse hover", () => {
    test.tags("desktop");
    test("should preview different font types on hover", async () => {
        const { el } = await setupFontTypeDropdown("<p>a[bc]d</p>");

        await hover(getFontTypeItem("Header 1 Display 1"));
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);

        await hover(getFontTypeItem("Header 2"));
        expect(getContent(el)).toBe(`<h2>a[bc]d</h2>`);

        await hover(getFontTypeItem("Header 3"));
        expect(getContent(el)).toBe(`<h3>a[bc]d</h3>`);

        await hover(getFontTypeItem("Normal"));
        expect(getContent(el)).toBe(`<div class="o-paragraph">a[bc]d</div>`);

        await hover(getFontTypeItem("Paragraph"));
        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);

        await hover(getFontTypeItem("Quote"));
        expect(getContent(el)).toBe(`<blockquote>a[bc]d</blockquote>`);
    });

    test.tags("desktop");
    test("should revert preview when mouse leaves without applying font type (no initial font type)", async () => {
        const { el } = await setupFontTypeDropdown("<p>a[bc]d</p>");

        await hover(getFontTypeItem("Header 1 Display 1"));
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);

        await hover(el);

        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);
    });

    test.tags("desktop");
    test("should revert preview when mouse leaves without applying font type (existing font type)", async () => {
        const { el } = await setupFontTypeDropdown(`<h1 class="display-1">a[bc]d</h1>`);

        await hover(getFontTypeItem("Paragraph"));
        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);

        await hover(el);

        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);
    });
});

describe("Font type preview with keyboard", () => {
    test.tags("desktop");
    test("should preview different font types while navigating with keyboard", async () => {
        const { el } = await setupFontTypeDropdown("<p>a[bc]d</p>");

        await press("ArrowDown");
        await animationFrame();
        expect(getFontTypeItem("Header 1 Display 1")).toBeFocused();
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);

        await press("ArrowDown");
        await animationFrame();
        expect(getFontTypeItem("Header 1")).toBeFocused();
        expect(getContent(el)).toBe(`<h1>a[bc]d</h1>`);
    });

    test.tags("desktop");
    test("should revert preview when Escape closes the dropdown (no initial font type)", async () => {
        const { el } = await setupFontTypeDropdown("<p>a[bc]d</p>");

        await press("ArrowDown");
        await animationFrame();
        expect(getFontTypeItem("Header 1 Display 1")).toBeFocused();
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);

        await press("Escape");
        await animationFrame();

        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);
    });

    test.tags("desktop");
    test("should revert preview when Escape closes the dropdown (existing font type)", async () => {
        const { el } = await setupFontTypeDropdown("<h2>a[bc]d</h2>");

        await press("ArrowDown");
        await animationFrame();

        expect(getFontTypeItem("Header 1 Display 1")).toBeFocused();
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);

        await press("Escape");
        await animationFrame();

        expect(getContent(el)).toBe(`<h2>a[bc]d</h2>`);
    });
});

describe("Font type preview with mixed interactions", () => {
    test.tags("desktop");
    test("should update preview when switching from hover to keyboard navigation", async () => {
        const { el } = await setupFontTypeDropdown("<p>a[bc]d</p>");

        await hover(getFontTypeItem("Header 1 Display 1"));
        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);

        await press("ArrowDown");
        await animationFrame();

        expect(getFontTypeItem("Header 1")).toBeFocused();
        expect(getContent(el)).toBe(`<h1>a[bc]d</h1>`);
    });

    test.tags("desktop");
    test("should revert preview when pressing Escape after switching from hover to keyboard navigation", async () => {
        const { el } = await setupFontTypeDropdown(`<h1 class="display-1">a[bc]d</h1>`);

        await hover(getFontTypeItem("Paragraph"));
        expect(getContent(el)).toBe(`<p>a[bc]d</p>`);

        await press("ArrowDown");
        await animationFrame();

        expect(getFontTypeItem("Code")).toBeFocused();
        expect(getContent(el)).toBe(`<pre>a[bc]d</pre>`);

        await press("Escape");
        await animationFrame();

        expect(getContent(el)).toBe(`<h1 class="display-1">a[bc]d</h1>`);
    });
});
