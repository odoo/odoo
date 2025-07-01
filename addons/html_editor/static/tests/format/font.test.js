import { animationFrame, click, queryOne, waitFor } from "@odoo/hoot-dom";
import { setupEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { expect, test } from "@odoo/hoot";
import { expandToolbar } from "../_helpers/toolbar";

test("should change the containing block with the font", async () => {
    const { el } = await setupEditor("<p>ab[cde]fg</p>");
    expect(queryOne(".btn[name='font']").textContent).toBe("Paragraph");
    await click(".btn[name='font']");
    await waitFor(".o_font_selector_menu");
    await click(".o_font_selector_menu .o-dropdown-item[name=blockquote]");
    await animationFrame();
    expect(queryOne(".btn[name='font']").textContent).toBe("Quote");
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
        expect(".btn[name='font']").toHaveCount(count);
    }
});
