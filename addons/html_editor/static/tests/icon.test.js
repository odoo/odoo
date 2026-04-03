import { describe, expect, test } from "@odoo/hoot";
import { click, tick, waitFor, waitForNone } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "./_helpers/editor";
import { animationFrame } from "@odoo/hoot-mock";
import { getContent, setContent, setSelection } from "./_helpers/selection";
import { splitBlock, undo } from "./_helpers/user_actions";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { expectElementCount } from "./_helpers/ui_expectations";
import { execCommand } from "./_helpers/userCommands";
import { unformat } from "./_helpers/format";
import { expandToolbar } from "./_helpers/toolbar";

test("icon toolbar is displayed", async () => {
    const { el } = await setupEditor(`<p><span class="oi" data-icon="local_bar"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is displayed (2)", async () => {
    const { el } = await setupEditor(`<p>abc<span class="oi" data-icon="local_bar"></span>def</p>`);
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeffdef</p>`
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
        `<p>abc\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeffdef</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is displayed (3)", async () => {
    const { el } = await setupEditor(`<p>abc<span class="oi" data-icon="local_bar"></span>def</p>`);
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeffdef</p>`
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
        `<p>abc\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeffdef</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is not displayed on rating stars", async () => {
    const { el } = await setupEditor(`<p><span class="oi" data-icon="local_bar"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
    setContent(
        el,
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="oi" data-icon="star" contenteditable="false">\u200B</i><i class="oi" data-icon="star" contenteditable="false">\u200B</i>[<i class="oi" data-icon="star" contenteditable="false">\u200B</i></span>]\u200B</p>`
    );
    await waitForNone(".o-we-toolbar .btn-group[name='icon_size']");
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("toolbar should not be namespaced for icon", async () => {
    await setupEditor(`<p>a[bc<span class="oi" data-icon="local_bar"></span>]def</p>`);
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("toolbar should not be namespaced for icon (2)", async () => {
    await setupEditor(`<p>abc[<span class="oi" data-icon="local_bar"></span>de]f</p>`);
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("Can resize an icon", async () => {
    const { el } = await setupEditor(`<p><span class="oi" data-icon="local_bar"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect("span[data-icon='local_bar']").toHaveCount(1);
    await click("button[name='icon_size_2']");
    expect("span[data-icon='local_bar'].oi-2x").toHaveCount(1);
    await click("button[name='icon_size_3']");
    expect("span[data-icon='local_bar'].oi-2x").toHaveCount(0);
    expect("span[data-icon='local_bar'].oi-3x").toHaveCount(1);
    await click("button[name='icon_size_4']");
    expect("span[data-icon='local_bar'].oi-3x").toHaveCount(0);
    expect("span[data-icon='local_bar'].oi-4x").toHaveCount(1);
    await click("button[name='icon_size_5']");
    expect("span[data-icon='local_bar'].oi-4x").toHaveCount(0);
    expect("span[data-icon='local_bar'].oi-5x").toHaveCount(1);
    await click("button[name='icon_size_1']");
    expect("span[data-icon='local_bar'].oi-5x").toHaveCount(0);
});

test("Can resize an oi icon", async () => {
    const { el } = await setupEditor(
        `<p><span class="oi oi-pastafarianism" contenteditable="false"></span></p>`
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi oi-pastafarianism" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi oi-pastafarianism" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    await click("button[name='icon_size_2']");
    expect("span.oi-pastafarianism.oi-2x").toHaveCount(1);
    await expectElementCount("button[name='icon_size_2'].active", 1);
    await click("button[name='icon_size_3']");
    expect("span.oi-pastafarianism.oi-2x").toHaveCount(0);
    expect("span.oi-pastafarianism.oi-3x").toHaveCount(1);
    await expectElementCount("button[name='icon_size_3'].active", 1);
    await click("button[name='icon_size_4']");
    expect("span.oi-pastafarianism.oi-3x").toHaveCount(0);
    expect("span.oi-pastafarianism.oi-4x").toHaveCount(1);
    await expectElementCount("button[name='icon_size_4'].active", 1);
    await click("button[name='icon_size_5']");
    expect("span.oi-pastafarianism.oi-4x").toHaveCount(0);
    expect("span.oi-pastafarianism.oi-5x").toHaveCount(1);
    await expectElementCount("button[name='icon_size_5'].active", 1);
    await click("button[name='icon_size_1']");
    expect("span.oi-pastafarianism.oi-5x").toHaveCount(0);
    await expectElementCount("button[name='icon_size_5'].active", 0);
});

test("Can spin an icon", async () => {
    const { el } = await setupEditor(`<p><span class="oi" data-icon="local_bar"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect("span[data-icon='local_bar']").toHaveCount(1);
    await click("button[name='icon_spin']");
    expect("span[data-icon='local_bar']").toHaveClass("oi-spin");
});

test("Can set icon color", async () => {
    const { el } = await setupEditor('<p><span class="oi" data-icon="local_bar"></span></p>');
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</p>`
    );
    // A selection inside the Material Symbols is automatically converted to a
    // selection around the Material Symbols, triggering the opening of the toolbar.
    const oi = el.querySelector(".oi");
    setSelection({ anchorNode: oi, anchorOffset: 0, focusNode: oi, focusOffset: 0 });
    await waitFor(".o-we-toolbar");
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-select-color-foreground");
    await animationFrame();
    await waitFor(".o_color_button[data-color='#6BADDE']");
    await click(".o_color_button[data-color='#6BADDE']");
    await expectElementCount(".o_font_color_selector", 0); // selector closed
    await waitFor(".o-we-toolbar .o-select-color-foreground [style*='rgb(107, 173, 222)']");
    expect(getContent(el)).toBe(
        `<p>[<font style="color: rgb(107, 173, 222);">\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</font>]</p>`
    );
});

test("Can undo to 1x size after applying 2x size", async () => {
    const { el, editor } = await setupEditor(`<p><span class="oi" data-icon="local_bar"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect("span[data-icon='local_bar']").toHaveCount(1);
    await click("button[name='icon_size_2']");
    expect("span[data-icon='local_bar'].oi-2x").toHaveCount(1);
    undo(editor);
    expect("span[data-icon='local_bar']").toHaveCount(1);
    expect("span[data-icon='local_bar'].oi-2x").toHaveCount(0);
});

test("Can replace icon using toolbar", async () => {
    const { el, editor } = await setupEditor(`<p><span class="oi oi-filled" data-icon="favorite"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi oi-filled" data-icon="favorite" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi oi-filled" data-icon="favorite" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    await contains("button[name='icon_replace']").click();
    await animationFrame();
    expect("main.modal-body").toHaveCount(1);
    expect("main.modal-body button.nav-link.active").toHaveText("Icons");
    // Corresponding icon should be highlighted in dialog
    expect("main.modal-body span[data-icon='favorite'].o_we_attachment_selected").toHaveCount(1);

    await contains("main.modal-body span[data-icon='search']").click();
    await animationFrame();
    expect("main.modal-body").toHaveCount(0);
    expect("span[data-icon='search']").toHaveCount(1); // Replace icon
    expect("span[data-icon='favorite']").toHaveCount(0);

    undo(editor);
    expect("span[data-icon='search']").toHaveCount(0);
    expect("span[data-icon='favorite']").toHaveCount(1);
});

test("Styles should be preserved when replacing icon", async () => {
    const { el } = await setupEditor(`<p><span class="oi oi-3x" data-icon="favorite"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi oi-3x" data-icon="favorite" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi oi-3x" data-icon="favorite" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    await contains("button[name='icon_replace']").click();
    await animationFrame();
    await contains("main.modal-body span[data-icon='search']").click();
    await animationFrame();
    expect("span[data-icon='search'].oi-3x").toHaveCount(1);
});

test("Can replace a odoo icon", async () => {
    const { editor, el } = await setupEditor(`<p><span class="oi" data-icon="add"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi" data-icon="add" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="oi" data-icon="add" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    execCommand(editor, "replaceIcon");
    await animationFrame();
    await contains("main.modal-body span[data-icon='search']").click();
    await animationFrame();
    expect("span.oi[data-icon='search']").toHaveCount(1);
    expect("span[data-icon='add']").toHaveCount(0);
});

test("Can replace a font awesome brand icon", async () => {
    const { el, editor } = await setupEditor(`<p><span class="fab fa-opera"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fab fa-opera" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="fab fa-opera" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    execCommand(editor, "replaceIcon");
    await animationFrame();
    await contains("main.modal-body span[data-icon='search']").click();
    await animationFrame();
    expect("span.oi[data-icon='search']").toHaveCount(1);
    expect("span.fab.fa-opera").toHaveCount(0);
});

test("Can replace a font awesome duotone icon", async () => {
    const { el, editor } = await setupEditor(`<p><span class="fad fa-bus-alt"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fad fa-bus-alt" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="fad fa-bus-alt" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    execCommand(editor, "replaceIcon");
    await animationFrame();
    await contains("main.modal-body span[data-icon='search']").click();
    await animationFrame();
    expect("span.oi[data-icon='search']").toHaveCount(1);
    expect("span.fad.fa-bus-alt").toHaveCount(0);
});

test("Can replace a font awesome regular icon", async () => {
    const { el, editor } = await setupEditor(`<p><span class="far fa-money-bill-alt"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="far fa-money-bill-alt" contenteditable="false">\u200b</span>\ufeff</p>`
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
        `<p>\ufeff[<span class="far fa-money-bill-alt" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    execCommand(editor, "replaceIcon");
    await animationFrame();
    await contains("main.modal-body span[data-icon='search']").click();
    await animationFrame();
    expect("span.oi[data-icon='search']").toHaveCount(1);
    expect("span.far.fa-money-bill-alt").toHaveCount(0);
});

test("Should be able to undo after adding spin effect to an icon", async () => {
    const { el, editor } = await setupEditor('<p><span class="oi" data-icon="local_bar"></span></p>');
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>\ufeff</p>`
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
    editor.shared.selection.stageSelection();
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeff</p>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_spin']").toHaveCount(1);
    expect(".btn-group[name='icon_spin']").not.toHaveClass("active");
    await click("button[name='icon_spin']");
    await animationFrame();
    expect("span[data-icon='local_bar'].oi-spin").toHaveCount(1);
    await expectElementCount(".btn-group[name='icon_spin'] button.active", 1);
    undo(editor);
    await animationFrame();
    expect("span[data-icon='local_bar'].oi-spin").toHaveCount(0);
    await expectElementCount(".btn-group[name='icon_spin'].active", 0);
    expect("span[data-icon='local_bar']").toHaveCount(1);
    expect("span[data-icon='local_bar'].oi-spin").toHaveCount(0);
});

describe("selection", () => {
    test("selection inside icon gets expanded to its outer boundaries", async () => {
        const { el } = await setupEditor(`<p>abc<span class="oi" data-icon="local_bar"></span>def</p>`);
        const icon = el.querySelector("span[data-icon='local_bar']");
        setSelection({ anchorNode: icon, anchorOffset: 0 });
        await tick();
        expect(getContent(el)).toBe(
            `<p>abc\ufeff[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]\ufeffdef</p>`
        );
    });

    test("selection inside icon gets expanded around it, but not around its contenteditable=false ancestor", async () => {
        const { el } = await setupEditor(
            `<p contenteditable="false">abc<span class="oi" data-icon="local_bar"></span>def</p>`
        );
        const icon = el.querySelector("span[data-icon='local_bar']");
        setSelection({ anchorNode: icon, anchorOffset: 0 });
        await tick();
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                '<p contenteditable="false">abc[<span class="oi" data-icon="local_bar" contenteditable="false">\u200b</span>]def</p>' +
                '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>'
        );
    });
});

test("should insert two empty paragraphs when Enter is pressed twice before the icon element", async () => {
    const { el, editor } = await setupEditor(
        `<p>[]<span class="oi" data-icon="local_bar" contenteditable="false"></span></p>`
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p><br></p><p>\ufeff[]<span class="oi" data-icon="local_bar" contenteditable="false">\u200B</span>\ufeff</p>`
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p><br></p><p><br></p><p>\ufeff[]<span class="oi" data-icon="local_bar" contenteditable="false">\u200B</span>\ufeff</p>`
    );
});

test("should wrap icons in feff when under list item", async () => {
    await testEditor({
        contentBefore: unformat(`
                <ul>
                    <li><span class="oi" data-icon="local_bar" contenteditable="false"></span></li>
                </ul>
            `),
        contentBeforeEdit: unformat(`
            <ul>
                <li>\ufeff<span class="oi" data-icon="local_bar" contenteditable="false">\u200B</span>\ufeff</li>
            </ul>
        `),
    });
});

test("should not allow to edit label if selection contain icon", async () => {
    await setupEditor(`<p>[ab<span class="oi" data-icon="local_bar" contenteditable="false"></span>]</p>`);
    await waitFor(".o-we-toolbar");
    await expandToolbar();
    await click('.o-we-toolbar button[name="link"]');
    await waitFor('[name="o_linkpopover_url_img"]');
    expect('[name="o_linkpopover_url_img"]').toHaveCount(1);
});

test("should not allow to edit label if selection contain oi icon", async () => {
    await setupEditor(
        `<p>[ab<span class="oi oi-pastafarianism" contenteditable="false"></span>]</p>`
    );
    await waitFor(".o-we-toolbar");
    await expandToolbar();
    await click('.o-we-toolbar button[name="link"]');
    await waitFor('[name="o_linkpopover_url_img"]');
    expect('[name="o_linkpopover_url_img"]').toHaveCount(1);
});

test("should be able to unlink an icon", async () => {
    onRpc(`${location.origin}/test`, () => ({
        title: "title",
        description: "description",
    }));
    onRpc(`/html_editor/link_preview_internal`, () => ({
        title: "title",
        description: "description",
    }));
    await setupEditor(
        `<p><a href="/test" class="my_link o_link_in_selection">[<span class="oi" data-icon="local_bar" contenteditable="false"></span>]</a></p>`
    );
    await waitFor(".o-we-toolbar");
    await click('[name="unlink"]');
    expect(".my_link").toHaveCount(0);
});
