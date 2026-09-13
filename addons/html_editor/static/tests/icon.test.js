import { describe, expect, test } from "@odoo/hoot";
import { click, tick, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";

import { setupEditor, testEditor } from "./_helpers/editor.js";
import { unformat } from "./_helpers/format.js";
import { getContent, setContent, setSelection } from "./_helpers/selection.js";
import { expectElementCount } from "./_helpers/ui_expectations.js";
import { splitBlock, undo } from "./_helpers/user_actions.js";
import { execCommand } from "./_helpers/userCommands.js";

test("icon toolbar is displayed", async () => {
    const { el } = await setupEditor(
        `<p><span class="fa-solid fa-martini-glass-empty"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is displayed (2)", async () => {
    const { el } = await setupEditor(
        `<p>abc<span class="fa-solid fa-martini-glass-empty"></span>def</p>`,
    );
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeffdef</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 2,
        focusNode: el.firstChild,
        focusOffset: 3,
    });
    expect(getContent(el)).toBe(
        `<p>abc\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeffdef</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is displayed (3)", async () => {
    const { el } = await setupEditor(
        `<p>abc<span class="fa-solid fa-martini-glass-empty"></span>def</p>`,
    );
    expect(getContent(el)).toBe(
        `<p>abc\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeffdef</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 2,
        focusNode: el.firstChild,
        focusOffset: 3,
    });
    expect(getContent(el)).toBe(
        `<p>abc\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeffdef</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
});

test("icon toolbar is not displayed on rating stars", async () => {
    const { el } = await setupEditor(
        `<p><span class="fa-solid fa-martini-glass-empty"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(1);
    setContent(
        el,
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa-regular fa-star" contenteditable="false">\u200B</i><i class="fa-regular fa-star" contenteditable="false">\u200B</i>[<i class="fa-regular fa-star" contenteditable="false">\u200B</i></span>]\u200B</p>`,
    );
    await waitForNone(".o-we-toolbar .btn-group[name='icon_size']");
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("toolbar should not be namespaced for icon", async () => {
    await setupEditor(
        `<p>a[bc<span class="fa-solid fa-martini-glass-empty"></span>]def</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("toolbar should not be namespaced for icon (2)", async () => {
    await setupEditor(
        `<p>abc[<span class="fa-solid fa-martini-glass-empty"></span>de]f</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_size']").toHaveCount(0);
});

test("Can resize an icon", async () => {
    const { el } = await setupEditor(
        `<p><span class="fa-solid fa-martini-glass-empty"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect("span.fa-martini-glass-empty").toHaveCount(1);
    await click("button[name='icon_size_2']");
    expect("span.fa-martini-glass-empty.fa-2x").toHaveCount(1);
    await click("button[name='icon_size_3']");
    expect("span.fa-martini-glass-empty.fa-2x").toHaveCount(0);
    expect("span.fa-martini-glass-empty.fa-3x").toHaveCount(1);
    await click("button[name='icon_size_4']");
    expect("span.fa-martini-glass-empty.fa-3x").toHaveCount(0);
    expect("span.fa-martini-glass-empty.fa-4x").toHaveCount(1);
    await click("button[name='icon_size_5']");
    expect("span.fa-martini-glass-empty.fa-4x").toHaveCount(0);
    expect("span.fa-martini-glass-empty.fa-5x").toHaveCount(1);
    await click("button[name='icon_size_1']");
    expect("span.fa-martini-glass-empty.fa-5x").toHaveCount(0);
});

test("Can spin an icon", async () => {
    const { el } = await setupEditor(
        `<p><span class="fa-solid fa-martini-glass-empty"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect("span.fa-martini-glass-empty").toHaveCount(1);
    await click("button[name='icon_spin']");
    expect("span.fa-martini-glass-empty").toHaveClass("fa-spin");
});

test("Can set icon color", async () => {
    const { el } = await setupEditor(
        `<p><span class="fa-solid fa-martini-glass-empty">[]</span></p>`,
    );
    await waitFor(".o-we-toolbar");
    expect(".o_font_color_selector").toHaveCount(0);
    await click(".o-select-color-foreground");
    await animationFrame();
    expect(".o_font_color_selector").toHaveCount(1);
    await click(".o_color_button[data-color='#6BADDE']");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(".o_font_color_selector").toHaveCount(0);
    expect(getContent(el)).toBe(
        `<p>[<font style="color: rgb(107, 173, 222);">\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeff</font>]</p>`,
    );
});

test("Can undo to 1x size after applying 2x size", async () => {
    const { el, editor } = await setupEditor(
        `<p><span class="fa-solid fa-martini-glass-empty"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect("span.fa-martini-glass-empty").toHaveCount(1);
    await click("button[name='icon_size_2']");
    expect("span.fa-martini-glass-empty.fa-2x").toHaveCount(1);
    undo(editor);
    expect("span.fa-martini-glass-empty").toHaveCount(1);
    expect("span.fa-martini-glass-empty.fa-2x").toHaveCount(0);
});

test("Can replace icon using toolbar", async () => {
    const { el, editor } = await setupEditor(
        `<p><span class="fa-solid fa-heart"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa-solid fa-heart" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-heart" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    await waitFor(".o-we-toolbar");
    await contains("button[name='icon_replace']").click();
    await animationFrame();
    expect("main.modal-body").toHaveCount(1);
    expect("main.modal-body a.nav-link.active").toHaveText("Icons");
    expect("main.modal-body span.fa-heart.o_we_attachment_selected").toHaveCount(1);

    await contains("main.modal-body span.fa-magnifying-glass").click();
    await animationFrame();
    expect("main.modal-body").toHaveCount(0);
    expect("span.fa-magnifying-glass").toHaveCount(1);
    expect("span.fa-heart").toHaveCount(0);

    undo(editor);
    expect("span.fa-magnifying-glass").toHaveCount(0);
    expect("span.fa-heart").toHaveCount(1);
});

test("Styles should be preserved when replacing icon", async () => {
    const { el } = await setupEditor(
        `<p><span class="fa-solid fa-heart fa-3x"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa-solid fa-heart fa-3x" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-heart fa-3x" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    await waitFor(".o-we-toolbar");
    await contains("button[name='icon_replace']").click();
    await animationFrame();
    await contains("main.modal-body span.fa-magnifying-glass").click();
    await animationFrame();
    expect("span.fa-magnifying-glass.fa-3x").toHaveCount(1);
});

test("Can replace a odoo icon", async () => {
    const { editor, el } = await setupEditor(`<p><span class="oi oi-plus"></span></p>`);
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="oi oi-plus" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="oi oi-plus" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    execCommand(editor, "replaceIcon");
    await animationFrame();
    await contains("main.modal-body span.fa-magnifying-glass").click();
    await animationFrame();
    expect("span.fa-solid.fa-magnifying-glass").toHaveCount(1);
    expect("span.oi.oi-plus").toHaveCount(0);
});

test("Can replace a font awesome brand icon", async () => {
    const { el, editor } = await setupEditor(
        `<p><span class="fab fa-opera"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fab fa-opera" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fab fa-opera" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    execCommand(editor, "replaceIcon");
    await animationFrame();
    await contains("main.modal-body span.fa-magnifying-glass").click();
    await animationFrame();
    expect("span.fa-solid.fa-magnifying-glass").toHaveCount(1);
    expect("span.fab.fa-opera").toHaveCount(0);
});

test("Can replace a font awesome duotone icon", async () => {
    const { el, editor } = await setupEditor(
        `<p><span class="fad fa-bus-alt"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fad fa-bus-alt" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fad fa-bus-alt" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    execCommand(editor, "replaceIcon");
    await animationFrame();
    await contains("main.modal-body span.fa-magnifying-glass").click();
    await animationFrame();
    expect("span.fa-solid.fa-magnifying-glass").toHaveCount(1);
    expect("span.fad.fa-bus-alt").toHaveCount(0);
});

test("Can replace a font awesome regular icon", async () => {
    const { el, editor } = await setupEditor(
        `<p><span class="far fa-money-bill-alt"></span></p>`,
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="far fa-money-bill-alt" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="far fa-money-bill-alt" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    execCommand(editor, "replaceIcon");
    await animationFrame();
    await contains("main.modal-body span.fa-magnifying-glass").click();
    await animationFrame();
    expect("span.fa-solid.fa-magnifying-glass").toHaveCount(1);
    expect("span.far.fa-money-bill-alt").toHaveCount(0);
});

test("Picking a brand icon stamps the brands face, not the solid one", async () => {
    const { el, editor } = await setupEditor(
        `<p><span class="fa-solid fa-heart"></span></p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    execCommand(editor, "replaceIcon");
    await animationFrame();
    expect("main.modal-body span.font-icons-icon.fa-brands.fa-instagram").toHaveCount(
        1,
    );
    expect("main.modal-body span.font-icons-icon.fa-solid.fa-instagram").toHaveCount(0);
    await contains("main.modal-body span.fa-brands.fa-instagram").click();
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-brands fa-instagram" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
});

test("A brand icon is preselected in its own face and swaps back to solid", async () => {
    const { el, editor } = await setupEditor(
        `<p><span class="fa-brands fa-instagram fa-2x"></span></p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    execCommand(editor, "replaceIcon");
    await animationFrame();
    expect("main.modal-body a.nav-link.active").toHaveText("Icons");
    expect("main.modal-body span.o_we_attachment_selected").toHaveCount(1);
    expect(
        "main.modal-body span.o_we_attachment_selected.fa-brands.fa-instagram",
    ).toHaveCount(1);
    await contains("main.modal-body span.fa-solid.fa-magnifying-glass").click();
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-magnifying-glass fa-2x" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
});

test("A brand icon stored under the solid face is still recognised", async () => {
    const { el, editor } = await setupEditor(
        `<p><span class="fa-solid fa-instagram"></span></p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    execCommand(editor, "replaceIcon");
    await animationFrame();
    expect(
        "main.modal-body span.o_we_attachment_selected.fa-brands.fa-instagram",
    ).toHaveCount(1);
    await contains("main.modal-body span.fa-solid.fa-heart").click();
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-heart" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
});

test("Should be able to undo after adding spin effect to an icon", async () => {
    const { el, editor } = await setupEditor(
        '<p><span class="fa-solid fa-martini-glass-empty"></span></p>',
    );
    expect(getContent(el)).toBe(
        `<p>\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>\ufeff</p>`,
    );
    setSelection({
        anchorNode: el.firstChild,
        anchorOffset: 1,
        focusNode: el.firstChild,
        focusOffset: 2,
    });
    editor.shared.history.stageSelection();
    expect(getContent(el)).toBe(
        `<p>\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeff</p>`,
    );
    await waitFor(".o-we-toolbar");
    expect(".btn-group[name='icon_spin']").toHaveCount(1);
    expect(".btn-group[name='icon_spin']").not.toHaveClass("active");
    await click("button[name='icon_spin']");
    await animationFrame();
    expect("span.fa-martini-glass-empty.fa-spin").toHaveCount(1);
    await expectElementCount(".btn-group[name='icon_spin'] button.active", 1);
    undo(editor);
    await animationFrame();
    expect("span.fa-martini-glass-empty.fa-spin").toHaveCount(0);
    await expectElementCount(".btn-group[name='icon_spin'].active", 0);
    expect("span.fa-martini-glass-empty").toHaveCount(1);
    expect("span.fa-martini-glass-empty.fa-spin").toHaveCount(0);
});

describe("selection", () => {
    test("selection inside icon gets expanded to its outer boundaries", async () => {
        const { el } = await setupEditor(
            `<p>abc<span class="fa-solid fa-martini-glass-empty"></span>def</p>`,
        );
        const icon = el.querySelector("span.fa-martini-glass-empty");
        setSelection({ anchorNode: icon, anchorOffset: 0 });
        await tick();
        expect(getContent(el)).toBe(
            `<p>abc\ufeff[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]\ufeffdef</p>`,
        );
    });

    test("selection inside icon gets expanded around it, but not around its contenteditable=false ancestor", async () => {
        const { el } = await setupEditor(
            `<p contenteditable="false">abc<span class="fa-solid fa-martini-glass-empty"></span>def</p>`,
        );
        const icon = el.querySelector("span.fa-martini-glass-empty");
        setSelection({ anchorNode: icon, anchorOffset: 0 });
        await tick();
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                '<p contenteditable="false">abc[<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200b</span>]def</p>' +
                '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
        );
    });
});

test("should insert two empty paragraphs when Enter is pressed twice before the icon element", async () => {
    const { el, editor } = await setupEditor(
        `<p>[]<span class="fa-solid fa-martini-glass-empty" contenteditable="false"></span></p>`,
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p><br></p><p>\ufeff[]<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200B</span>\ufeff</p>`,
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p><br></p><p><br></p><p>\ufeff[]<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200B</span>\ufeff</p>`,
    );
});

test("should wrap icons in feff when under list item", async () => {
    await testEditor({
        contentBefore: unformat(`
                <ul>
                    <li><span class="fa-solid fa-martini-glass-empty" contenteditable="false"></span></li>
                </ul>
            `),
        contentBeforeEdit: unformat(`
            <ul>
                <li>\ufeff<span class="fa-solid fa-martini-glass-empty" contenteditable="false">\u200B</span>\ufeff</li>
            </ul>
        `),
    });
});
