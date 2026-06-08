import { waitFor } from "@odoo/hoot-dom";
import { setupEditor } from "../_helpers/editor";
import { getContent } from "../_helpers/selection";
import { expect, test } from "@odoo/hoot";
import { expandToolbar } from "../_helpers/toolbar";
import { contains } from "@web/../tests/web_test_helpers";
import { expectElementCount } from "../_helpers/ui_expectations";
import { getIframeInput } from "../_helpers/iframe_input";

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

test("Should show the default font display name", async () => {
    await setupEditor(`
        <ul>
            <li class="display-2-fs">
                <div class="o-paragraph">abc</div>
                <ul class="o_default_font_size">
                    <li>[def]</li>
                </ul>
            </li>
        </ul>    
    `);
    await expectElementCount(".o-we-toolbar", 1);
    const fontSizeInputEl = await getIframeInput(
        ".o-we-toolbar [name='font_size'] iframe.o_font_size_selector_iframe",
        "input[name='font_size_input']"
    );
    expect(fontSizeInputEl.value).toBe("14");
});
