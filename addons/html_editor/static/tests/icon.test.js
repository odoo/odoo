import { expect, test } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";
import { setupEditor } from "./_helpers/editor";
import { animationFrame } from "@odoo/hoot-mock";
import { getContent, setContent, setSelection } from "./_helpers/selection";
import { undo } from "./_helpers/user_actions";

test("icon toolbar is displayed", async () => {
    const { el } = await setupEditor(`<p><span class="fa fa-glass"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa fa-glass" contenteditable="false">\u200b</span>\ufeff</p>`
    );
    // Selection normalization include U+FEFF, moving the cursor outside the
    // icon and triggering the normal toolbar. To prevent this, we exclude
    // U+FEFF from selection.
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa fa-glass" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is displayed (2)", async () => {
    const { el } = await setupEditor(`<p>abc<span class="fa fa-glass"></span>def</p>`);
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<span class="fa fa-glass" contenteditable="false">\u200b</span>\ufeffdef</p>`
    );
    // Selection normalization include U+FEFF, moving the cursor outside the
    // icon and triggering the normal toolbar. To prevent this, we exclude
    // U+FEFF from selection.
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 2,
        focusNode: el.firstChild,
        focusOffset: 3,
    });
    expect(getContent(el)).toBe(
        `<p>abc\ufeff[<span class="fa fa-glass" contenteditable="false">\u200b</span>]\ufeffdef</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is displayed (3)", async () => {
    const { el } = await setupEditor(`<p>abc<span class="fa fa-glass"></span>def</p>`);
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<span class="fa fa-glass" contenteditable="false">\u200b</span>\ufeffdef</p>`
    );
    // Selection normalization include U+FEFF, moving the cursor outside the
    // icon and triggering the normal toolbar. To prevent this, we exclude
    // U+FEFF from selection.
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 2,
        focusNode: el.firstChild,
        focusOffset: 3,
    });
    expect(getContent(el)).toBe(
        `<p>abc\ufeff[<span class="fa fa-glass" contenteditable="false">\u200b</span>]\ufeffdef</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is not displayed on rating stars", async () => {
    const { el } = await setupEditor(`<p><span class="fa fa-glass"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa fa-glass" contenteditable="false">\u200b</span>\ufeff</p>`
    );
    // Selection normalization include U+FEFF, moving the cursor outside the
    // icon and triggering the normal toolbar. To prevent this, we exclude
    // U+FEFF from selection.
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa fa-glass" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
    setContent(
        el,
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i>[<i class="fa fa-star-o" contenteditable="false">\u200B</i></span>]\u200B</p>`
    );
    await animationFrame();
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("toolbar should not be namespaced for icon", async () => {
    await setupEditor(`<p>a[bc<span class="fa fa-glass"></span>]def</p>`);
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("toolbar should not be namespaced for icon (2)", async () => {
    await setupEditor(`<p>abc[<span class="fa fa-glass"></span>de]f</p>`);
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("Can resize an icon", async () => {
    const { el } = await setupEditor(`<p><span class="fa fa-glass"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa fa-glass" contenteditable="false">\u200b</span>\ufeff</p>`
    );
    // Selection normalization include U+FEFF, moving the cursor outside the
    // icon and triggering the normal toolbar. To prevent this, we exclude
    // U+FEFF from selection.
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa fa-glass" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect("span.fa-glass").toHaveCount(1);
    await click("button[name='icon_size_2']");
    expect("span.fa-glass.fa-2x").toHaveCount(1);
    await click("button[name='icon_size_3']");
    expect("span.fa-glass.fa-2x").toHaveCount(0);
    expect("span.fa-glass.fa-3x").toHaveCount(1);
    await click("button[name='icon_size_4']");
    expect("span.fa-glass.fa-3x").toHaveCount(0);
    expect("span.fa-glass.fa-4x").toHaveCount(1);
    await click("button[name='icon_size_5']");
    expect("span.fa-glass.fa-4x").toHaveCount(0);
    expect("span.fa-glass.fa-5x").toHaveCount(1);
    await click("button[name='icon_size_1']");
    expect("span.fa-glass.fa-5x").toHaveCount(0);
});

test("Can spin an icon", async () => {
    const { el } = await setupEditor(`<p><span class="fa fa-glass"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa fa-glass" contenteditable="false">\u200b</span>\ufeff</p>`
    );
    // Selection normalization include U+FEFF, moving the cursor outside the
    // icon and triggering the normal toolbar. To prevent this, we exclude
    // U+FEFF from selection.
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa fa-glass" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect("span.fa-glass").toHaveCount(1);
    await click("button[name='icon_spin']");
    expect("span.fa-glass").toHaveClass("fa-spin");
});

test("Can set icon color", async () => {
    await setupEditor(`<p><span class="fa fa-glass">[]</span></p>`);
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    expect(".o-we-toolbar").toHaveCount(1); // toolbar still open
    expect(".o_font_color_selector").toHaveCount(0); // selector closed
    expect("span.fa-glass").toHaveStyle({ color: "rgb(107, 173, 222)" });
});

test("Can undo to 1x size after applying 2x size", async () => {
    const { el, editor } = await setupEditor(`<p><span class="fa fa-glass"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa fa-glass" contenteditable="false">\u200b</span>\ufeff</p>`
    );
    // Selection normalization include U+FEFF, moving the cursor outside the
    // icon and triggering the normal toolbar. To prevent this, we exclude
    // U+FEFF from selection.
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa fa-glass" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect("span.fa-glass").toHaveCount(1);
    await click("button[name='icon_size_2']");
    expect("span.fa-glass.fa-2x").toHaveCount(1);
    undo(editor);
    expect("span.fa-glass").toHaveCount(1);
    expect("span.fa-glass.fa-2x").toHaveCount(0);
});
