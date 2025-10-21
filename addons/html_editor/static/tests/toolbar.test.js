import { withSequence } from "@html_editor/utils/resource";
import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    delay,
    getActiveElement,
    keyDown,
    keyUp,
    manuallyDispatchProgrammaticEvent,
    pointerDown,
    pointerUp,
    press,
    queryAll,
    queryAllTexts,
    queryOne,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { advanceTime, animationFrame, tick } from "@odoo/hoot-mock";
import {
    contains,
    onRpc,
    patchTranslations,
    patchWithCleanup,
    defineModels,
    fields,
    models,
    mountView,
} from "@web/../tests/web_test_helpers";
import { fontSizeItems } from "../src/main/font/font_plugin";
import { Plugin } from "../src/plugin";
import { MAIN_PLUGINS } from "../src/plugin_sets";
import { convertNumericToUnit, getCSSVariableValue, getHtmlStyle } from "../src/utils/formatting";
import { setupEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import {
    getContent,
    moveSelectionOutsideEditor,
    setContent,
    setSelection,
    simulateDoubleClickSelect,
    simulateTripleClickSelect,
    firstClick,
    secondClick,
    thirdClick,
} from "./_helpers/selection";
import { strong } from "./_helpers/tags";
import { insertText } from "./_helpers/user_actions";
import { expandToolbar } from "./_helpers/toolbar";
import { nodeSize } from "@html_editor/utils/position";
import { expectElementCount } from "./_helpers/ui_expectations";
import { ToolbarPlugin } from "@html_editor/main/toolbar/toolbar_plugin";
import { ImageCrop } from "@html_editor/main/media/image_crop";
import { Editor } from "@html_editor/editor";

test.tags("desktop");
test("toolbar is only visible when selection is not collapsed in desktop", async () => {
    const { el } = await setupEditor("<p>test</p>");

    // set a non-collapsed selection to open toolbar
    await expectElementCount(".o-we-toolbar", 0);
    setContent(el, "<p>[test]</p>");
    await expectElementCount(".o-we-toolbar", 1);

    // set a collapsed selection to close toolbar
    setContent(el, "<p>test[]</p>");
    await expectElementCount(".o-we-toolbar", 0);
});

test.tags("mobile");
test("toolbar is also visible when selection is collapsed in mobile", async () => {
    const { el } = await setupEditor("<p>test</p>");

    // set a non-collapsed selection to open toolbar
    await expectElementCount(".o-we-toolbar", 0);
    setContent(el, "<p>[test]</p>");
    await expectElementCount(".o-we-toolbar", 1);

    setContent(el, "<p>test[]</p>");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
});

test("toolbar closes when selection leaves editor", async () => {
    const { el } = await setupEditor("<p>test</p>");
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    await click(document.body);
    moveSelectionOutsideEditor();
    await expectElementCount(".o-we-toolbar", 0);
});

test("toolbar works: can format bold", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    await expectElementCount(".o-we-toolbar", 0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    // click on toggle bold
    await contains(".btn[name='bold']").click();
    expect(getContent(el)).toBe("<p><strong>[test]</strong></p>");
});

test.tags("iframe");
test("toolbar in an iframe works: can format bold", async () => {
    const { el } = await setupEditor("<p>test</p>", { props: { iframe: true } });
    expect("iframe").toHaveCount(1);
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    await expectElementCount(".o-we-toolbar", 0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    // click on toggle bold
    await contains(".btn[name='bold']").click();
    expect(getContent(el)).toBe("<p><strong>[test]</strong></p>");
});

test("toolbar buttons react to selection change", async () => {
    const { el } = await setupEditor("<p>test some text</p>");

    // set selection to open toolbar
    setContent(el, "<p>[test] some text</p>");
    await expandToolbar();

    // check that bold button is not active
    expect(".btn[name='bold']").not.toHaveClass("active");
    // check that remove format buton isdisabled and have correct title
    expect(".btn[name='remove_format']").toHaveAttribute("disabled");
    expect(".btn[name='remove_format']").toHaveAttribute("title", "Selection has no format");

    // click on toggle bold
    await contains(".btn[name='bold']").click();
    await waitFor(".btn[name='bold'].active");
    expect(getContent(el)).toBe("<p><strong>[test]</strong> some text</p>");
    expect(".btn[name='bold']").toHaveClass("active");
    expect(".btn[name='remove_format']").not.toHaveAttribute("disabled");
    expect(".btn[name='remove_format']").toHaveAttribute("title", "Remove Format");

    // set selection where text is not bold
    setContent(el, "<p><strong>test</strong> some [text]</p>");
    await waitFor(".btn[name='bold']:not(.active)");
    expect(".btn[name='bold']").not.toHaveClass("active");

    // set selection again where text is bold
    setContent(el, "<p><strong>[test]</strong> some text</p>");
    await waitFor(".btn[name='bold'].active");
    expect(".btn[name='bold']").toHaveClass("active");
});

test("toolbar buttons react to selection change (2)", async () => {
    const { el } = await setupEditor("<p><strong>test [some]</strong> some text</p>");

    await waitFor(".o-we-toolbar");
    expect(".btn[name='bold']").toHaveClass("active");

    // extends selection to include non-bold text
    setContent(el, "<p><strong>test [some</strong> some] text</p>");
    // @todo @phoenix: investigate why waiting for animation frame is (sometimes) not enough
    await waitFor(".btn[name='bold']:not(.active)");
    expect(".btn[name='bold']").not.toHaveClass("active");

    // change selection to come back into bold text
    setContent(el, "<p><strong>test [so]me</strong> some text</p>");
    await waitFor(".btn[name='bold'].active");
    expect(".btn[name='bold']").toHaveClass("active");
});

test("toolbar list buttons react to selection change", async () => {
    const { el } = await setupEditor("<ul><li>[abc]</li></ul>");

    await expandToolbar();
    click(".btn[name='list_selector'].dropdown-toggle");
    await waitFor(".btn[name='list_selector'].dropdown-toggle.show");

    expect(".btn[name='bulleted_list']").toHaveClass("active");
    expect(".btn[name='numbered_list']").not.toHaveClass("active");
    expect(".btn[name='checklist']").not.toHaveClass("active");

    // Toggle to numbered list
    await click(".btn[name='numbered_list']");
    await waitFor(".btn[name='numbered_list'].active");
    expect(getContent(el)).toBe("<ol><li>[abc]</li></ol>");
    expect(".btn[name='bulleted_list']").not.toHaveClass("active");
    expect(".btn[name='numbered_list']").toHaveClass("active");
    expect(".btn[name='checklist']").not.toHaveClass("active");

    // Toggle to checklist
    await click(".btn[name='checklist']");
    await waitFor(".btn[name='checklist'].active");
    expect(getContent(el)).toBe('<ul class="o_checklist"><li>[abc]</li></ul>');
    expect(".btn[name='bulleted_list']").not.toHaveClass("active");
    expect(".btn[name='numbered_list']").not.toHaveClass("active");
    expect(".btn[name='checklist']").toHaveClass("active");

    // Toggle list off
    await click(".btn[name='checklist']");
    await waitFor(".btn[name='checklist']:not(.active)");
    expect(getContent(el)).toBe("<p>[abc]</p>");
    expect(".btn[name='bulleted_list']").not.toHaveClass("active");
    expect(".btn[name='numbered_list']").not.toHaveClass("active");
    expect(".btn[name='checklist']").not.toHaveClass("active");
});

test("toolbar link buttons react to selection change", async () => {
    const { el } = await setupEditor("<p>th[is is a] <a>link</a> test!</p>");

    await waitFor(".o-we-toolbar");
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='link']").not.toHaveClass("active");
    expect(".btn[name='unlink']").toHaveCount(0);

    setContent(el, "<p>th[is is a <a>li]nk</a> test!</p>");
    await waitFor(".btn[name='link'].active");
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='link']").toHaveClass("active");
    expect(".btn[name='unlink']").toHaveCount(1);

    setContent(el, "<p>th[is is a <a>link</a> tes]t!</p>");
    await waitFor(".btn[name='link']:not(.active)");
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='link']").not.toHaveClass("active");
    expect(".btn[name='unlink']").toHaveCount(1);
});

test("toolbar unlink button should be disabled when link is unremovable", async () => {
    await setupEditor('<p>a<a class="oe_unremovable" href="http://test.test/">bc[d]</a>e</p>');
    await waitFor(".o-we-toolbar");
    expect(".btn[name='link']").toHaveCount(1);
    expect(".btn[name='link']").toHaveClass("active");
    expect(".btn[name='unlink']").toHaveCount(1);
    expect(".btn[name='unlink']").toHaveClass("disabled");
});

test("toolbar format buttons should react to format change", async () => {
    await setupEditor(
        `<div class="o-paragraph">[\ufeff<a href="http://test.com">\ufefftest.com\ufeff</a>\ufeff&nbsp;]</div>`
    );
    await waitFor(".o-we-toolbar");
    expect(".btn[name='bold']").not.toHaveClass("active");
    await contains(".btn[name='bold']").click();
    await animationFrame();
    expect(".btn[name='bold']").toHaveClass("active");
});

test("toolbar format buttons should react to format change across blocks (with whitespace)", async () => {
    await setupEditor(`
        <p>[abc</p>
        <p>def]</p>
        `);
    await waitFor(".o-we-toolbar");
    expect(".btn[name='bold']").not.toHaveClass("active");
    await contains(".btn[name='bold']").click();
    await animationFrame();
    expect(".btn[name='bold']").toHaveClass("active");
});

test("toolbar disable link button when selection cross blocks", async () => {
    await setupEditor("<div>[<div>a<p>b</p></div>]</div>");
    await waitFor(".o-we-toolbar");
    expect(".btn[name='link']").toHaveClass("disabled");
});

test("toolbar disable link button when table cells are selected", async () => {
    await setupEditor(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><p>[<br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td><p>]<br></p></td>
                    <td><p><br></p></td>
                </tr>
            </tbody>
        </table>
    `);
    await waitFor(".o-we-toolbar");
    expect(".btn[name='link']").toHaveClass("disabled");
});

test("toolbar enable link button when selection has only link", async () => {
    await setupEditor(`<p>[<a href="test.com">test.com</a>]</p>`);

    await waitFor(".o-we-toolbar");
    expect(".btn[name='link']").not.toHaveClass("disabled");
});

test("toolbar works: can select font", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    await expectElementCount(".o-we-toolbar", 0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar .btn[name='font']").toHaveText("Paragraph");

    await contains(".o-we-toolbar [name='font'] .dropdown-toggle").click();
    await contains(".o_font_selector_menu .dropdown-item:contains('Header 2')").click();
    expect(getContent(el)).toBe("<h2>[test]</h2>");
    expect(".o-we-toolbar .btn[name='font']").toHaveText("Header 2");
});

test("toolbar works: show the right font name", async () => {
    const { editor } = await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    const items = editor.getResource("font_items");
    for (const item of items) {
        await contains(".o-we-toolbar [name='font'] .dropdown-toggle").click();
        await animationFrame();
        const name = item.name.toString();
        let selector = `.o_font_selector_menu .dropdown-item:contains('${name}')`;
        for (const tempItem of items) {
            // we need to exclude the font names which have the current name as a substring.
            if (tempItem === item) {
                continue;
            }
            const tempItemName = tempItem.name.toString();
            if (tempItemName.includes(name)) {
                selector += `:not(:contains(${tempItemName}))`;
            }
        }
        await contains(selector).click();
        await animationFrame();
        expect(".o-we-toolbar .btn[name='font']").toHaveText(name);
    }
});

test("toolbar works: show the right font name after undo", async () => {
    const { el } = await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar .btn[name='font']").toHaveText("Paragraph");

    await contains(".o-we-toolbar [name='font'] .dropdown-toggle").click();
    await contains(".o_font_selector_menu .dropdown-item:contains('Header 2')").click();
    expect(getContent(el)).toBe("<h2>[test]</h2>");
    expect(".o-we-toolbar .btn[name='font']").toHaveText("Header 2");
    await press(["ctrl", "z"]);
    await animationFrame();
    expect(getContent(el)).toBe("<p>[test]</p>");
    expect(".o-we-toolbar .btn[name='font']").toHaveText("Paragraph");
    await press(["ctrl", "y"]);
    await animationFrame();
    expect(getContent(el)).toBe("<h2>[test]</h2>");
    expect(".o-we-toolbar .btn[name='font']").toHaveText("Header 2");
});

test("toolbar works: can select font size", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");
    const style = getHtmlStyle(document);
    const getFontSizeFromVar = (cssVar) => {
        const strValue = getCSSVariableValue(cssVar, style);
        const remValue = parseFloat(strValue);
        const pxValue = convertNumericToUnit(remValue, "rem", "px", style);
        return Math.round(pxValue);
    };

    // set selection to open toolbar
    await expectElementCount(".o-we-toolbar", 0);
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    const iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    const inputEl = iframeEl.contentWindow.document?.querySelector("input");
    expect(inputEl).toHaveValue(getFontSizeFromVar("body-font-size").toString());

    await contains(".o-we-toolbar [name='font_size_selector'].dropdown-toggle").click();
    const sizes = [...new Set(fontSizeItems.map((item) => getFontSizeFromVar(item.variableName)))]
        .sort((a, b) => a - b)
        .map(String);
    expect(queryAllTexts(".o_font_size_selector_menu .dropdown-item")).toEqual([...sizes]);
    const h1Size = getFontSizeFromVar("h1-font-size").toString();
    await contains(`.o_font_size_selector_menu .dropdown-item:contains('${h1Size}')`).click();
    expect(getContent(el)).toBe(`<p><span class="h1-fs">[test]</span></p>`);
    expect(inputEl).toHaveValue(h1Size);
    await contains(".o-we-toolbar [name='font_size_selector'].dropdown-toggle").click();
    const oSmallSize = getFontSizeFromVar("small-font-size").toString();
    await contains(`.o_font_size_selector_menu .dropdown-item:contains('${oSmallSize}')`).click();
    expect(getContent(el)).toBe(`<p><span class="o_small-fs">[test]</span></p>`);
    expect(inputEl).toHaveValue(oSmallSize);
});

test("toolbar works: change font size correctly when closest block element has already font size class", async () => {
    const { el } = await setupEditor(`<h2 class="h3-fs">abc <strong>def [ghi]</strong></h2>`);
    const style = getHtmlStyle(document);
    const getFontSizeFromVar = (cssVar) => {
        const strValue = getCSSVariableValue(cssVar, style);
        const remValue = parseFloat(strValue);
        const pxValue = convertNumericToUnit(remValue, "rem", "px", style);
        return Math.round(pxValue);
    };

    await waitFor(".o-we-toolbar");
    const iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    const inputEl = iframeEl.contentWindow.document?.querySelector("input");
    expect(inputEl).toHaveValue(getFontSizeFromVar("h3-font-size").toString());

    await contains(".o-we-toolbar [name='font_size_selector'].dropdown-toggle").click();
    const sizes = [...new Set(fontSizeItems.map((item) => getFontSizeFromVar(item.variableName)))]
        .sort((a, b) => a - b)
        .map(String);
    expect(queryAllTexts(".o_font_size_selector_menu .dropdown-item")).toEqual([...sizes]);
    const h1Size = getFontSizeFromVar("h1-font-size").toString();
    await contains(`.o_font_size_selector_menu .dropdown-item:contains('${h1Size}')`).click();
    expect(getContent(el)).toBe(
        `<h2 class="h3-fs">abc <strong>def </strong><span class="h1-fs"><strong>[ghi]</strong></span></h2>`
    );
    expect(inputEl).toHaveValue(h1Size);
});

test("toolbar works: show the correct text alignment", async () => {
    const { el } = await setupEditor("<p>[test</p><p><br>]</p>");
    await expandToolbar();
    expect("button[name='text_align']").toHaveCount(1);
    expect("button[name='text_align'] span").toHaveInnerHTML(`<i class="fa fa-align-left"> </i>`);
    await click("button[name='text_align']");
    await contains(".o-we-toolbar-dropdown .btn.fa-align-right").click();
    expect(getContent(el)).toBe(
        `<p style="text-align: right;">[test</p><p style="text-align: right;"><br>]</p>`
    );
    expect("button[name='text_align'] span").toHaveInnerHTML(`<i class="fa fa-align-right"> </i>`);
});

test("toolbar works: show the correct text alignment after undo/redo", async () => {
    const { el } = await setupEditor("<p>[test]</p>");
    await expandToolbar();
    expect("button[name='text_align']").toHaveCount(1);
    expect("button[name='text_align'] span").toHaveInnerHTML(`<i class="fa fa-align-left"> </i>`);
    await click("button[name='text_align']");
    await contains(".o-we-toolbar-dropdown .btn.fa-align-center").click();
    expect(getContent(el)).toBe(`<p style="text-align: center;">[test]</p>`);
    expect("button[name='text_align'] span").toHaveInnerHTML(`<i class="fa fa-align-center"> </i>`);
    await press(["ctrl", "z"]);
    await animationFrame();
    expect(getContent(el)).toBe(`<p>[test]</p>`);
    expect("button[name='text_align'] span").toHaveInnerHTML(`<i class="fa fa-align-left"> </i>`);
    await press(["ctrl", "y"]);
    await animationFrame();
    expect(getContent(el)).toBe(`<p style="text-align: center;">[test]</p>`);
    expect("button[name='text_align'] span").toHaveInnerHTML(`<i class="fa fa-align-center"> </i>`);
});

test("should focus the editable area after selecting a font size item", async () => {
    const { editor, el } = await setupEditor("<p>[test]</p>");
    await expectElementCount(".o-we-toolbar", 1);
    const iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    const inputEl = iframeEl.contentWindow.document?.querySelector("input");
    await contains(".o-we-toolbar [name='font_size_selector']").click();
    expect(getActiveElement()).toBe(inputEl);
    await waitFor(".o_font_size_selector_menu .dropdown-item:contains('21')");
    await contains(".o_font_size_selector_menu .dropdown-item:contains('21')").click();
    expect(getActiveElement()).toBe(editor.editable);
    expect(getActiveElement()).not.toBe(inputEl);
    expect(getContent(el)).toBe(`<p><span class="h2-fs">[test]</span></p>`);
});

test.tags("desktop");
test("toolbar works: display correct font size on select all", async () => {
    const { el } = await setupEditor("<p>test</p>");
    expect(getContent(el)).toBe("<p>test</p>");

    // set selection to open toolbar
    await expectElementCount(".o-we-toolbar", 0);
    setContent(el, "<p>[test]</p>");
    const style = getHtmlStyle(document);
    const getFontSizeFromVar = (cssVar) => {
        const strValue = getCSSVariableValue(cssVar, style);
        const remValue = parseFloat(strValue);
        const pxValue = convertNumericToUnit(remValue, "rem", "px", style);
        return Math.round(pxValue);
    };
    await waitFor(".o-we-toolbar");
    const iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    const inputEl = iframeEl.contentWindow.document?.querySelector("input");
    await contains(".o-we-toolbar [name='font_size_selector'].dropdown-toggle").click();
    await animationFrame();
    const h1Size = getFontSizeFromVar("h1-font-size").toString();
    await contains(`.o_font_size_selector_menu .dropdown-item:contains('${h1Size}')`).click();
    expect(getContent(el)).toBe(`<p><span class="h1-fs">[test]</span></p>`);
    setContent(el, `<p><span class="h1-fs">te[]st</span></p>`);
    await waitForNone(".o-we-toolbar");
    await press(["ctrl", "a"]); // Select all
    await waitFor(".o-we-toolbar");
    expect(inputEl).toHaveValue(`${h1Size}`);
});

test("toolbar works: displays correct font size on input", async () => {
    const { el } = await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    const iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    expect(iframeEl).toHaveCount(1);
    const inputEl = iframeEl.contentWindow.document?.querySelector("input");
    await contains(inputEl).click();
    // Ensure that the input has the default font size value.
    expect(inputEl).toHaveValue("14");
    expect(".o_font_size_selector_menu").toHaveCount(1);
    // Ensure that the selection is still present in the editable.
    expect(getContent(el)).toBe(`<p>[test]</p>`);
    expect(getActiveElement()).toBe(inputEl);

    await press("8");
    expect(inputEl).toHaveValue("8");
    await advanceTime(200);
    expect(".o_font_size_selector_menu").toHaveCount(1);
    expect(getContent(el)).toBe(`<p><span style="font-size: 8px;">[test]</span></p>`);
    await expectElementCount(".o-we-toolbar", 1);
});

test("toolbar works: font size dropdown closes on Enter and Tab key press", async () => {
    await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    const iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    expect(iframeEl).toHaveCount(1);
    const inputEl = iframeEl.contentWindow.document?.querySelector("input");
    await contains(inputEl).click();
    expect(".o_font_size_selector_menu").toHaveCount(1);

    await press("Enter");
    await animationFrame();
    expect(".o_font_size_selector_menu").toHaveCount(0);

    await contains(inputEl).click();
    expect(".o_font_size_selector_menu").toHaveCount(1);
    await press("Tab");
    await animationFrame();
    expect(".o_font_size_selector_menu").toHaveCount(0);
});

test("toolbar works: ArrowUp/Down moves focus to font size dropdown", async () => {
    await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");

    const iframeEl = queryOne(".o-we-toolbar [name='font_size_selector'] iframe");
    expect(iframeEl).toHaveCount(1);
    const inputEl = iframeEl.contentWindow.document?.querySelector("input");
    await contains(inputEl).click();
    expect(".o_font_size_selector_menu").toHaveCount(1);
    expect(getActiveElement()).toBe(inputEl);

    const fontSizeSelectorMenu = queryOne(".o_font_size_selector_menu div");
    await press("ArrowDown");
    await animationFrame();
    expect(".o_font_size_selector_menu").toHaveCount(1);
    expect(getActiveElement()).toBe(fontSizeSelectorMenu.firstElementChild);

    await contains(inputEl).click();
    expect(".o_font_size_selector_menu").toHaveCount(1);
    await press("ArrowUp");
    await animationFrame();
    expect(".o_font_size_selector_menu").toHaveCount(1);
    expect(getActiveElement()).toBe(fontSizeSelectorMenu.lastElementChild);
});

test.tags("desktop");
test("toolbar should not open on keypress tab inside table", async () => {
    const contentBefore = unformat(`
        <table>
            <tbody>
                <tr>
                    <td><p>[]ab</p></td>
                    <td><p>cd</p></td>
                </tr>
            </tbody>
        </table>
    `);
    const contentAfter = unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td><p>ab</p></td>
                    <td><p>cd[]</p></td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>
    `);

    const { el } = await setupEditor(contentBefore);
    await press("Tab");
    expect(getContent(el)).toBe(contentAfter);
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 0);
});

test("toolbar open on single selected cell in table", async () => {
    const contentBefore = unformat(`
        <table class="table table-bordered o_table">
            <tbody>
                <tr>
                    <td><p>[]<br></p></td>
                    <td><p><br></p></td>
                </tr>
                <tr>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
            </tbody>
        </table>
    `);

    const { el } = await setupEditor(contentBefore);
    const targetTd = el.querySelector("td");
    const mouseDownPositionX = targetTd.getBoundingClientRect().left + 10;
    const mouseDownPositionY = targetTd.getBoundingClientRect().top + 10;
    const mouseMoveDiff = 40;
    manuallyDispatchProgrammaticEvent(targetTd, "mousedown", {
        detail: 1,
        clientX: mouseDownPositionX,
        clientY: mouseDownPositionY,
    });
    // Simulate mousemove horizontally for 40px.
    manuallyDispatchProgrammaticEvent(targetTd, "mousemove", {
        detail: 1,
        clientX: mouseDownPositionX + mouseMoveDiff,
        clientY: mouseDownPositionY,
    });
    manuallyDispatchProgrammaticEvent(targetTd, "mouseup", {
        detail: 1,
        clientX: mouseDownPositionX + mouseMoveDiff,
        clientY: mouseDownPositionY,
    });
    await animationFrame();
    await tick();
    expect(targetTd).toHaveClass("o_selected_td");
    await expectElementCount(".o-we-toolbar", 1);
});

test("should select table single cell when entire content is selected via mouse movement", async () => {
    const content = unformat(`
        <table class="table table-bordered o_table" style="width: 250px;">
            <tbody>
                <tr>
                    <td style="width: 200px;">
                        <p>abcdefghijklmno</p>
                        <p>abcdefghijklmnopqrs</p>
                        <p>abcdefg</p>
                    </td>
                    <td style="width: 50px;"><p><br></p></td>
                </tr>
                <tr>
                    <td><p><br></p></td>
                    <td><p><br></p></td>
                </tr>
            </tbody>
        </table>
    `);

    const { el } = await setupEditor(content);

    const firstTd = el.querySelector("td");
    const firstP = firstTd.firstChild;
    const lastP = firstTd.lastChild;

    // Simulate mousedown at the top of the first paragraph.
    const rectStart = firstP.getBoundingClientRect();
    manuallyDispatchProgrammaticEvent(firstP, "mousedown", {
        detail: 1,
        clientX: rectStart.left,
        clientY: rectStart.top,
    });

    // Set selection from start of first <p> to end of last <p>.
    setSelection({
        anchorNode: firstP.firstChild,
        anchorOffset: 0,
        focusNode: lastP.firstChild,
        focusOffset: nodeSize(lastP.firstChild),
    });
    await animationFrame();

    // Get bounding rect of selection range.
    const range = document.createRange();
    range.setStart(lastP.firstChild, 0);
    range.setEnd(lastP.firstChild, nodeSize(lastP.firstChild));
    const rect = range.getBoundingClientRect();

    // Simulate mousemove and mouseup events to complete the selection.
    manuallyDispatchProgrammaticEvent(lastP, "mousemove", {
        detail: 1,
        clientX: rect.right,
        clientY: rect.top,
    });
    manuallyDispatchProgrammaticEvent(lastP, "mousemove", {
        detail: 1,
        clientX: rect.right + 5,
        clientY: rect.top,
    });
    manuallyDispatchProgrammaticEvent(lastP, "mouseup", {
        detail: 1,
        clientX: rect.right + 5,
        clientY: rect.top,
    });

    await animationFrame();
    await tick();

    expect(firstTd).toHaveClass("o_selected_td");
    await expectElementCount(".o-we-toolbar", 1);
});

test.tags("desktop");
test("toolbar should close on keypress tab inside table", async () => {
    const contentBefore = unformat(`
        <table>
            <tbody>
                <tr>
                    <td><p>[ab]</p></td>
                    <td><p>cd</p></td>
                </tr>
            </tbody>
        </table>
    `);
    const contentAfter = unformat(`
        <p data-selection-placeholder=""><br></p>
        <table>
            <tbody>
                <tr>
                    <td><p>ab</p></td>
                    <td><p>cd[]</p></td>
                </tr>
            </tbody>
        </table>
        <p data-selection-placeholder=""><br></p>
    `);

    const { el } = await setupEditor(contentBefore);
    await waitFor(".o-we-toolbar");
    await press("Tab");
    expect(getContent(el)).toBe(contentAfter);
    await expectElementCount(".o-we-toolbar", 0);
});

test("toolbar works: show the correct vertical alignment", async () => {
    const { el } = await setupEditor(
        unformat(`
            <table class="table table-bordered o_table">
                <tbody>
                    <tr style="height: 100px;">
                        <td>[1</td>
                        <td></td>
                        <td>3</td>
                    </tr>
                    <tr style="height: 100px;">
                        <td>4</td>
                        <td>5]</td>
                        <td>6</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await expandToolbar();
    expect("button[name='vertical_align'] svg[name='vertical_align_top']").toHaveCount(1);
    await click("button[name='vertical_align']");
    await animationFrame();
    await contains(".dropdown-menu button svg[name='vertical_align_middle']").click();
    expect("button[name='vertical_align'] svg[name='vertical_align_middle']").toHaveCount(1);
    expect(".dropdown-menu button.active svg[name='vertical_align_middle']").toHaveCount(1);
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr style="height: 100px;">
                        <td class="o_selected_td" style="vertical-align: middle;">[1</td>
                        <td class="o_selected_td" style="vertical-align: middle;"></td>
                        <td>3</td>
                    </tr>
                    <tr style="height: 100px;">
                        <td class="o_selected_td" style="vertical-align: middle;">4</td>
                        <td class="o_selected_td" style="vertical-align: middle;">5]</td>
                        <td>6</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("toolbar works: show the correct vertical alignment after undo/redo", async () => {
    const { el } = await setupEditor(
        unformat(`
            <table class="table table-bordered o_table">
                <tbody>
                    <tr style="height: 100px;">
                        <td>1</td>
                        <td>[</td>
                    </tr>
                    <tr style="height: 100px;">
                        <td>3</td>
                        <td>4]</td>
                    </tr>
                </tbody>
            </table>
        `)
    );
    await expandToolbar();
    expect("button[name='vertical_align'] svg[name='vertical_align_top']").toHaveCount(1);
    await click("button[name='vertical_align']");
    await animationFrame();
    await contains(".dropdown-menu button svg[name='vertical_align_bottom']").click();
    expect("button[name='vertical_align'] svg[name='vertical_align_bottom']").toHaveCount(1);
    expect(".dropdown-menu button.active svg[name='vertical_align_bottom']").toHaveCount(1);
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr style="height: 100px;">
                        <td>1</td>
                        <td class="o_selected_td" style="vertical-align: bottom;">[</td>
                    </tr>
                    <tr style="height: 100px;">
                        <td>3</td>
                        <td class="o_selected_td" style="vertical-align: bottom;">4]</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    await press(["ctrl", "z"]);
    await animationFrame();
    expect("button[name='vertical_align'] svg[name='vertical_align_top']").toHaveCount(1);
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table">
                <tbody>
                    <tr style="height: 100px;">
                        <td>1</td>
                        <td>[</td>
                    </tr>
                    <tr style="height: 100px;">
                        <td>3</td>
                        <td>4]</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
    await press(["ctrl", "y"]);
    await animationFrame();
    expect("button[name='vertical_align'] svg[name='vertical_align_bottom']").toHaveCount(1);
    expect(".dropdown-menu button.active svg[name='vertical_align_bottom']").toHaveCount(1);
    expect(getContent(el)).toBe(
        unformat(`
            <p data-selection-placeholder=""><br></p>
            <table class="table table-bordered o_table o_selected_table">
                <tbody>
                    <tr style="height: 100px;">
                        <td>1</td>
                        <td class="o_selected_td" style="vertical-align: bottom;">[</td>
                    </tr>
                    <tr style="height: 100px;">
                        <td>3</td>
                        <td class="o_selected_td" style="vertical-align: bottom;">4]</td>
                    </tr>
                </tbody>
            </table>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("toolbar buttons shouldn't be active without text node in the selection", async () => {
    await setupEditor("<div>[<p><br></p>]</div>");
    await waitFor(".o-we-toolbar");
    expect(queryAll(".o-we-toolbar .btn.active").length).toBe(0);
});

test("toolbar behave properly if selection has no range", async () => {
    const { el } = await setupEditor("<p>test</p>");

    await expectElementCount(".o-we-toolbar", 0);
    setContent(el, "<p>[test]</p>");
    await expectElementCount(".o-we-toolbar", 1);

    const selection = document.getSelection();
    selection.removeAllRanges();

    setContent(el, "<p>abc</p>");
    await expectElementCount(".o-we-toolbar", 0);
});

test("toolbar correctly show namespace button group and stop showing when namespace change", async () => {
    class TestPlugin extends Plugin {
        static id = "TestPlugin";
        resources = {
            toolbar_namespaces: [
                {
                    id: "aNamespace",
                    isApplied: (nodeList) => !!nodeList.find((node) => node.tagName === "DIV"),
                },
            ],
            user_commands: { id: "test_cmd", run: () => null },
            toolbar_groups: withSequence(24, { id: "test_group", namespaces: ["aNamespace"] }),
            toolbar_items: [
                {
                    id: "test_btn",
                    groupId: "test_group",
                    commandId: "test_cmd",
                    description: "Test Button",
                    icon: "fa-square",
                },
            ],
        };
    }
    const { el } = await setupEditor("<div>[<section><p>abc</p></section><div>d]ef</div></div>", {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });
    await expectElementCount(".o-we-toolbar .btn-group[name='test_group']", 1);
    setContent(el, "<div><section><p>[abc]</p></section><div>def</div></div>");
    await expectElementCount(".o-we-toolbar .btn-group[name='test_group']", 0);
});

test("toolbar does not evaluate isActive when namespace does not match", async () => {
    class TestPlugin extends Plugin {
        static id = "TestPlugin";
        resources = {
            user_commands: { id: "test_cmd", run: () => null },
            toolbar_groups: withSequence(24, { id: "test_group", namespaces: ["image"] }),
            toolbar_items: [
                {
                    id: "test_btn",
                    groupId: "test_group",
                    commandId: "test_cmd",
                    description: "Test Button",
                    icon: "fa-square",
                    isActive: () => expect.step("image format evaluated"),
                },
            ],
        };
    }
    await setupEditor(
        `
        <div>
            <p>[Foo]</p>
            <img class="img-fluid" src="/web/static/img/logo.png">
        </div>
    `,
        {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        }
    );
    await waitFor(".o-we-toolbar");
    expect.verifySteps([]);
    await click("img");
    await animationFrame();
    expect.verifySteps(["image format evaluated"]);
});

describe("compact toolbar", () => {
    test("toolbar opens in 'compact' namespace by default", async () => {
        await setupEditor("<p>[test]</p>");
        await waitFor(".o-we-toolbar");
        expect(".o-we-toolbar").toHaveAttribute("data-namespace", "compact");
        await expandToolbar();
        expect(".o-we-toolbar").toHaveAttribute("data-namespace", "expanded");
    });

    const patchToUseOnlyTestButtons = () =>
        patchWithCleanup(Editor.prototype, {
            getResource(resourceName) {
                const result = super.getResource(resourceName);
                if (resourceName === "toolbar_groups") {
                    return result.filter((group) =>
                        ["expand_toolbar", "test_group"].includes(group.id)
                    );
                }
                return result;
            },
        });
    let id = 0;
    const makeTestButton = (obj) => ({
        id: `btn_${id++}`,
        groupId: "test_group",
        commandId: "test_cmd",
        description: "Test Button",
        icon: "fa-square",
        ...obj,
    });
    const repeat = (count, fn) => Array.from({ length: count }, fn);

    test("toolbar should not open in compact mode if expanded toolbar has less than 7 items", async () => {
        class TestPlugin extends Plugin {
            static id = "TestPlugin";
            resources = {
                user_commands: { id: "test_cmd", run: () => null },
                toolbar_groups: { id: "test_group" },
                toolbar_items: [
                    // 3 buttons in compact and expanded namespaces
                    ...repeat(3, () => makeTestButton({ namespaces: ["compact", "expanded"] })),
                    // 3 buttons in expanded only namespace
                    ...repeat(3, () => makeTestButton({ namespaces: ["expanded"] })),
                ],
            };
        }
        patchToUseOnlyTestButtons();
        await setupEditor("<p>[test]</p>", {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        await waitFor(".o-we-toolbar");
        expect(".o-we-toolbar").toHaveAttribute("data-namespace", "expanded");
    });
    test("toolbar should open in compact mode if expanded toolbar is big enough (>= 7 items)", async () => {
        class TestPlugin extends Plugin {
            static id = "TestPlugin";
            resources = {
                user_commands: { id: "test_cmd", run: () => null },
                toolbar_groups: { id: "test_group" },
                toolbar_items: [
                    // 3 buttons in compact and expanded namespaces
                    ...repeat(3, () => makeTestButton({ namespaces: ["compact", "expanded"] })),
                    // 4 buttons in expanded only namespace
                    ...repeat(4, () => makeTestButton({ namespaces: ["expanded"] })),
                ],
            };
        }
        patchToUseOnlyTestButtons();
        await setupEditor("<p>[test]</p>", {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        await waitFor(".o-we-toolbar");
        expect(".o-we-toolbar").toHaveAttribute("data-namespace", "compact");
    });
    test("toolbar should not open in compact mode if expanded toolbar has only one extra item", async () => {
        class TestPlugin extends Plugin {
            static id = "TestPlugin";
            resources = {
                user_commands: { id: "test_cmd", run: () => null },
                toolbar_groups: { id: "test_group" },
                toolbar_items: [
                    // 10 buttons in compact and expanded namespaces
                    ...repeat(10, () => makeTestButton({ namespaces: ["compact", "expanded"] })),
                    // 1 button in expanded only namespace
                    makeTestButton({ namespaces: ["expanded"] }),
                ],
            };
        }
        patchToUseOnlyTestButtons();
        await setupEditor("<p>[test]</p>", {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        await waitFor(".o-we-toolbar");
        expect(".o-we-toolbar").toHaveAttribute("data-namespace", "expanded");
    });
    test("toolbar should open in compact mode if expanded toolbar has more than one extra item", async () => {
        class TestPlugin extends Plugin {
            static id = "TestPlugin";
            resources = {
                user_commands: { id: "test_cmd", run: () => null },
                toolbar_groups: { id: "test_group" },
                toolbar_items: [
                    // 10 buttons in compact and expanded namespaces
                    ...repeat(10, () => makeTestButton({ namespaces: ["compact", "expanded"] })),
                    // 2 buttons in expanded only namespace
                    makeTestButton({ namespaces: ["expanded"] }),
                    makeTestButton({ namespaces: ["expanded"] }),
                ],
            };
        }
        patchToUseOnlyTestButtons();
        await setupEditor("<p>[test]</p>", {
            config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
        });
        await waitFor(".o-we-toolbar");
        expect(".o-we-toolbar").toHaveAttribute("data-namespace", "compact");
        await expandToolbar();
        expect(".o-we-toolbar").toHaveAttribute("data-namespace", "expanded");
    });
});

test.tags("desktop");
test("expanded toolbar reopens in 'compact' namespace by default after closing", async () => {
    const { el } = await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveAttribute("data-namespace", "compact");
    await expandToolbar();
    expect(".o-we-toolbar").toHaveAttribute("data-namespace", "expanded");
    // Collapse selection
    setContent(el, "<p>test[]</p>");
    await waitForNone(".o-we-toolbar");
    // Reopen toolbar
    setContent(el, "<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    expect(".o-we-toolbar").toHaveAttribute("data-namespace", "compact");
});

test("toolbar items without namespace default to 'expanded'", async () => {
    class TestPlugin extends Plugin {
        static id = "TestPlugin";
        resources = {
            user_commands: { id: "test_cmd", run: () => null },
            toolbar_groups: { id: "test_group" },
            toolbar_items: [
                {
                    id: "test_btn",
                    groupId: "test_group",
                    commandId: "test_cmd",
                    description: "Test Button",
                    icon: "fa-square",
                },
            ],
        };
    }
    await setupEditor("<p>[test]</p>", {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });
    await waitFor(".o-we-toolbar");
    // Test button in not present in compact toolbar
    expect(".o-we-toolbar .btn[name='test_btn']").toHaveCount(0);
    await expandToolbar();
    // Test button is present in expanded toolbar by default
    expect(".o-we-toolbar .btn[name='test_btn']").toHaveCount(1);
});

test("toolbar should open with image namespace the selection spans an image and whitespace", async () => {
    const { el } = await setupEditor(`<p>[abc]</p>`);
    // Make sure we start with a compact toolbar so we know that at the end when
    // we don't anymore it did in fact change and we're not just lagging behind
    // the DOM.
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
    expect(queryOne(".o-we-toolbar").dataset.namespace).toBe("compact");
    expect(queryAll(".o-we-toolbar .btn-group[name='font']").length).toBe(1);
    expect(queryAll(".o-we-toolbar .btn-group[name='decoration']").length).toBe(1);
    setContent(
        el,
        `<p>[
            <img>
        ]</p>`
    );
    await waitFor(".o-we-toolbar[data-namespace='image']");
    expect(queryOne(".o-we-toolbar").dataset.namespace).toBe("image");
    expect(queryAll(".o-we-toolbar .btn-group[name='font']").length).toBe(0);
    expect(queryAll(".o-we-toolbar .btn-group[name='decoration']").length).toBe(0);
});

test("plugins can create buttons with text in toolbar", async () => {
    class TestPlugin extends Plugin {
        static id = "TestPlugin";
        resources = {
            user_commands: { id: "test_cmd", run: () => null },
            toolbar_groups: withSequence(24, { id: "test_group" }),
            toolbar_items: [
                {
                    id: "test_btn",
                    groupId: "test_group",
                    commandId: "test_cmd",
                    description: "Test Button",
                    text: "Text button",
                },
            ],
        };
    }
    await setupEditor(`<div> <p class="foo">[Foo]</p> </div>`, {
        config: { Plugins: [...MAIN_PLUGINS, TestPlugin] },
    });
    await expandToolbar();
    expect("button[name='test_btn']").toHaveText("Text button");
});

test("toolbar buttons should have rounded corners at the edges of a group", async () => {
    await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    const buttonGroups = queryAll(".o-we-toolbar .btn-group");
    for (const group of buttonGroups) {
        for (let i = 0; i < group.children.length; i++) {
            const button = group.children[i];
            const computedStyle = getComputedStyle(button);
            const borderRadius = Object.fromEntries(
                ["top-left", "top-right", "bottom-left", "bottom-right"].map((corner) => [
                    corner,
                    Number.parseInt(computedStyle[`border-${corner}-radius`]),
                ])
            );
            // Should have rounded corners on the left only if first button
            if (i === 0) {
                expect(borderRadius["top-left"]).toBeGreaterThan(0);
                expect(borderRadius["bottom-left"]).toBeGreaterThan(0);
            } else {
                expect(borderRadius["top-left"]).toBe(0);
                expect(borderRadius["bottom-left"]).toBe(0);
            }
            // Should have rounded corners on the right only if last button
            if (i === group.children.length - 1) {
                expect(borderRadius["top-right"]).toBeGreaterThan(0);
                expect(borderRadius["bottom-right"]).toBeGreaterThan(0);
            } else {
                expect(borderRadius["top-right"]).toBe(0);
                expect(borderRadius["bottom-right"]).toBe(0);
            }
        }
    }
});

test("toolbar buttons should have title attribute", async () => {
    await setupEditor("<ul><li>[abc]</li></ul>");
    const toolbar = await waitFor(".o-we-toolbar");
    for (const button of toolbar.querySelectorAll("button")) {
        expect(button).toHaveAttribute("title");
    }
});

test("toolbar buttons should have title attribute with translated text", async () => {
    // Retrieve toolbar buttons descriptions in English
    const { editor, plugins } = await setupEditor("");
    // map function to get the title string value
    const itemDescriptionString = (item) =>
        item.description instanceof Function
            ? item.description().toString()
            : item.description.toString();

    // item.label could be a LazyTranslatedString so we ensure it is a string with toString()
    const descriptions = plugins.get("toolbar").getButtons().map(itemDescriptionString);
    editor.destroy();

    // Patch translations to return "Translated" for these terms
    patchTranslations({
        html_editor: Object.fromEntries(descriptions.map((title) => [title, "Translated"])),
    });

    // Instantiate a new editor.
    const { plugins: postPatchPlugins } = await setupEditor("<p>[abc]</p>");

    // Check that every registered button has the result of the call to _t
    postPatchPlugins
        .get("toolbar")
        .getButtons()
        .forEach((item) => {
            // item.label could be a LazyTranslatedString so we ensure it is a string with toString()
            expect(itemDescriptionString(item)).toBe("Translated");
        });

    await waitFor(".o-we-toolbar");

    // Check that every button has a title attribute with the translated description
    for (const button of queryAll(".o-we-toolbar button")) {
        expect(button).toHaveAttribute("title", "Translated");
    }
});

test.tags("desktop");
test("keep the toolbar if the selection crosses two blocks, even if their contents aren't selected", async () => {
    const { el } = await setupEditor("<p>a</p><p>b</p>");
    await expectElementCount(".o-we-toolbar", 0);

    setContent(el, "<p>[a</p><p>]b</p>");
    await tick(); // selectionChange
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);

    // This selection is possible when you double-click at the end of a line.
    setContent(el, "<p>a[</p><p>]b</p>");
    await tick(); // selectionChange
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
});

test.tags("desktop");
test("keep the toolbar if the selection crosses two blocks, even if their contents aren't selected (ignore whitespace)", async () => {
    const { el } = await setupEditor("<p>a</p>\n<p>b</p>");
    await expectElementCount(".o-we-toolbar", 0);

    setContent(el, "<p>[a</p>\n<p>]b</p>");
    await tick(); // selectionChange
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);

    // This selection is possible when you double-click at the end of a line.
    setContent(el, "<p>a[</p>\n<p>]b</p>");
    await tick(); // selectionChange
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);
});

test.tags("desktop");
test("toolbar should close on open link popover", async () => {
    await setupEditor("<p>[a]</p>");
    await expectElementCount(".o-we-toolbar", 1);
    await click(".o-we-toolbar .fa-link");
    await expectElementCount(".o-we-toolbar", 0);
});

test.tags("desktop", "iframe");
test("toolbar should close on open link popover (iframe)", async () => {
    await setupEditor("<p>[a]</p>", { props: { iframe: true } });
    await expectElementCount(".o-we-toolbar", 1);
    await click(".o-we-toolbar .fa-link");
    await expectElementCount(".o-we-toolbar", 0);
});

test.tags("desktop");
test("toolbar should close on edit link from preview", async () => {
    await setupEditor(`<p><a href="http://test.test/">[a]</a></p>`);
    await expectElementCount(".o-we-toolbar", 1);
    await click(".o-we-toolbar .fa-link");
    await waitFor(".o-we-linkpopover");
    await click(".o_we_edit_link");
    await expectElementCount(".o-we-toolbar", 0);
});

test.tags("desktop");
test("close the toolbar if the selection contains any nodes (traverseNode = [], ignore zws)", async () => {
    const { el } = await setupEditor(`<p>ab${strong("\u200B", "first")}cd</p>`);
    await expectElementCount(".o-we-toolbar", 0);

    setContent(el, `<p>a[b${strong("\u200B", "first")}c]d</p>`);
    await tick(); // selectionChange
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 1);

    setContent(el, `<p>ab${strong("[\u200B]", "first")}cd</p>`);
    await tick(); // selectionChange
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 0);
});

test.tags("desktop");
test("should not close image cropper while loading media", async () => {
    const base64Image =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=";

    // This promise is needed to ensure that the `show` method has completed
    // before clicking on `Discard` button as it sets `isCropperActive` true
    // at the end. In `closeCropper` method `isCropperActive` must be true
    // to close the cropper.
    const cropperReadyPromise = new Promise((resolve) => {
        patchWithCleanup(ImageCrop.prototype, {
            async show(...args) {
                await super.show(...args);
                resolve();
            },
        });
    });
    // Mock backend image RPCs
    onRpc("/html_editor/get_image_info", async () => {
        await delay(50);
        return {
            original: { image_src: base64Image },
        };
    });

    // Setup editor with an image
    await setupEditor(`<p>[<img src="${base64Image}">]</p>`);
    await waitFor(".o-we-toolbar");

    await animationFrame();
    await click('.btn[name="image_crop"]');

    await waitFor('.btn:contains("Discard")', { timeout: 1000 });
    await click('.btn:contains("Discard")');
    await animationFrame();

    // Cropper should not close as the cropper still loading the image.
    expect('.btn:contains("Discard")').toHaveCount(1);

    // Once the image loaded we should be able to close
    await cropperReadyPromise;
    await click('.btn:contains("Discard")');
    await waitForNone('.btn:contains("Discard")', { timeout: 1500 });
});

test("toolbar shouldn't be visible if can_display_toolbar === false", async () => {
    const { el } = await setupEditor("<p>[test]<img></p>", {
        config: { resources: { can_display_toolbar: (namespace) => namespace !== "image" } },
    });

    await expectElementCount(".o-we-toolbar", 1);
    setContent(el, "<p>test[<img>]</p>");
    await animationFrame();
    await expectElementCount(".o-we-toolbar", 0);
});

test.tags("desktop", "iframe");
test("toolbar should close when clicked outside the iframe", async () => {
    await setupEditor("<p>[a]</p>", { props: { iframe: true } });
    await expectElementCount(".o-we-toolbar", 1);
    // click outside the iframe
    await click(".o-main-components-container");
    await expectElementCount(".o-we-toolbar", 0);
});

describe.tags("desktop");
describe("toolbar open and close on user interaction", () => {
    describe("mouse", () => {
        test("toolbar should not open while mousedown (only after mouseup)", async () => {
            const { el } = await setupEditor("<p>test</p>");
            await expectElementCount(".o-we-toolbar", 0);

            await pointerDown(el);
            // <p>[]test</p>
            setSelection({ anchorNode: el.children[0], anchorOffset: 0 });
            await tick(); // selectionChange
            // Simulate extending the selection with mousedown
            // <p>[test]</p>
            setSelection({ anchorNode: el.children[0], anchorOffset: 0, focusOffset: 1 });
            await tick(); // selectionChange

            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);

            await pointerUp(el);
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should open on mouseup after selecting text (even if mouseup happens outside the editable)", async () => {
            const { el } = await setupEditor("<p>test</p>");
            await expectElementCount(".o-we-toolbar", 0);

            await pointerDown(el);
            // <p>[]test</p>
            setSelection({ anchorNode: el.children[0], anchorOffset: 0 });
            await tick(); // selectionChange
            // Simulate extending the selection with mousedown
            // <p>[test]</p>
            setSelection({ anchorNode: el.children[0], anchorOffset: 0, focusOffset: 1 });
            await tick(); // selectionChange

            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);

            await pointerUp(el.ownerDocument);
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should close on mousedown", async () => {
            const { el } = await setupEditor("<p>[test]</p><p>text</p>");
            await waitFor(".o-we-toolbar");

            await pointerDown(el);
            // <p>test</p><p>[]text</p>
            setSelection({ anchorNode: el.children[1], anchorOffset: 0 });
            await tick(); // selectionChange
            await expectElementCount(".o-we-toolbar", 0);

            await pointerUp(el);
            await tick();
            expect(getContent(el)).toBe("<p>test</p><p>[]text</p>");
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);
        });

        test("toolbar should close on mousedown (2)", async () => {
            const { el } = await setupEditor("<p>[test]</p>");

            /** @todo fix warnings */
            patchWithCleanup(console, { warn: () => {} });

            await waitFor(".o-we-toolbar");

            // Mousedown on the selected text: it does not change the selection until mouseup
            await pointerDown(el);
            await tick();
            await expectElementCount(".o-we-toolbar", 0);

            await pointerUp(el);
            setContent(el, "<p>[]test</p>");
            await tick();
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);
        });

        test("toolbar should open on double click", async () => {
            const { el } = await setupEditor("<p>test</p>");
            const p = el.firstElementChild;

            await simulateDoubleClickSelect(p);
            expect(getContent(el)).toBe("<p>[test]</p>");
            // toolbar open after double click is debounced
            await advanceTime(500);
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should open on triple click", async () => {
            const { el } = await setupEditor("<p>test text</p>");
            const p = el.firstElementChild;

            await simulateTripleClickSelect(p);
            expect(getContent(el)).toBe("<p>[test text]</p>");
            // toolbar open after triple click is debounced
            await advanceTime(500);
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should not open between double and triple click", async () => {
            const { el } = await setupEditor("<p>test text</p>");
            const p = el.firstElementChild;

            // Double click
            await firstClick(p);
            await secondClick(p);
            expect(getContent(el)).toBe("<p>[test] text</p>");
            await advanceTime(100);
            // Toolbar is not open yet, waiting for a possible third click
            await expectElementCount(".o-we-toolbar", 0);

            // Third click
            await thirdClick(p);
            expect(getContent(el)).toBe("<p>[test text]</p>");
            await advanceTime(500);
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should not open after triple click while mouse is down", async () => {
            const { el } = await setupEditor("<p>test text</p>");
            const p = el.firstElementChild;

            await simulateDoubleClickSelect(p);
            await pointerDown(p);
            manuallyDispatchProgrammaticEvent(p, "mousedown", { detail: 3 });
            setSelection({ anchorNode: p, anchorOffset: 0, focusOffset: 1 });
            await tick(); // selectionChange
            expect(getContent(el)).toBe("<p>[test text]</p>");
            await advanceTime(500);
            // Toolbar is not open yet, waiting for mouseup
            await expectElementCount(".o-we-toolbar", 0);

            // Mouse up
            manuallyDispatchProgrammaticEvent(p, "mouseup", { detail: 3 });
            manuallyDispatchProgrammaticEvent(p, "click", { detail: 3 });
            await advanceTime(500);
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should not move on click toolbar button", async () => {
            const { el } = await setupEditor(
                `<p style="padding-top: 100px">aaaaaaaaaaaaa [test] bbbbbbbbbbbbb</p>`
            );
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 1);

            const overlay = queryOne(".o-we-toolbar").parentElement;
            const position = {
                top: overlay.style.top,
                left: overlay.style.left,
            };

            await contains(".o-we-toolbar button[name='bold']").click();
            expect(getContent(el)).toBe(
                `<p style="padding-top: 100px">aaaaaaaaaaaaa <strong>[test]</strong> bbbbbbbbbbbbb</p>`
            );
            expect({ top: overlay.style.top, left: overlay.style.left }).toEqual(position);
            expect(overlay.style.visibility).toBe("visible");
        });
    });

    describe("keyboard", () => {
        test("toolbar should not open on keydown Arrow (only after keyup)", async () => {
            const { el } = await setupEditor("<p>[]test</p>");
            await expectElementCount(".o-we-toolbar", 0);

            await keyDown(["Shift", "ArrowRight"]);
            setContent(el, "<p>[t]est</p>");
            await tick(); // selectionChange

            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);

            await keyUp(["Shift", "ArrowRight"]);

            await advanceTime(500); // Toolbar open on keyup is debounced
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should close on keydown Arrow", async () => {
            const { el } = await setupEditor("<p>[tes]t</p>");
            await waitFor(".o-we-toolbar");

            // Toolbar should close on keydown
            await keyDown(["Shift", "ArrowRight"]);
            setContent(el, "<p>[test]</p>");
            await tick(); // selectionChange
            await waitForNone(".o-we-toolbar");
            await expectElementCount(".o-we-toolbar", 0);

            // Toolbar should open after keyup
            await keyUp(["Shift", "ArrowRight"]);

            await advanceTime(500); // toolbar open on keyup is debounced
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should not close on keydown shift or control", async () => {
            await setupEditor("<p>[tes]t</p>");
            await waitFor(".o-we-toolbar");

            // Toolbar should not close on keydown shift
            await keyDown(["Shift"]);
            await tick();
            await expectElementCount(".o-we-toolbar", 1);

            await keyUp(["Shift"]);
            await tick();
            await expectElementCount(".o-we-toolbar", 1);

            // Toolbar should not close on keydown ctrl
            await keyDown(["Control"]);
            await tick();
            await expectElementCount(".o-we-toolbar", 1);

            await keyUp(["Control"]);
            await tick();
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should not open between keystrokes separated by a short interval", async () => {
            const { el } = await setupEditor("<p>[]test</p>");
            await expectElementCount(".o-we-toolbar", 0);

            // Keystroke # 1
            await keyDown(["Shift", "ArrowRight"]);
            setContent(el, "<p>[t]est</p>");
            await tick(); // selectionChange
            await keyUp(["Shift", "ArrowRight"]);
            await advanceTime(100);
            await expectElementCount(".o-we-toolbar", 0);

            // Keystroke # 2
            await keyDown(["Shift", "ArrowRight"]);
            setContent(el, "<p>[te]st</p>");
            await tick(); // selectionChange
            await keyUp(["Shift", "ArrowRight"]);
            await advanceTime(100);
            await expectElementCount(".o-we-toolbar", 0);

            // Toolbar opens some time after the last keyup
            await advanceTime(500);
            await expectElementCount(".o-we-toolbar", 1);
        });

        test("toolbar should not open with a collapsed selection inside a contenteditable=false", async () => {
            await setupEditor(`<div contenteditable="false"><p>[]test</p></div>`);
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);
        });

        test("toolbar should not open with a non-collapsed selection inside a contenteditable=false", async () => {
            await setupEditor(`<div contenteditable="false"><p>[test]</p></div>`);
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);
        });
    });
});

describe.tags("mobile");
describe("history", () => {
    test("toolbar should have history buttons on mobile", async () => {
        const { el, editor } = await setupEditor("<p>test</p>");
        setContent(el, "<p>test[]</p>");
        await expectElementCount(".o-we-toolbar", 1);

        // Check that the history buttons are present and disabled
        expect(".btn[name='undo']").toHaveClass("disabled");
        expect(".btn[name='redo']").toHaveClass("disabled");

        // Make changes
        await insertText(editor, "X");
        expect(getContent(el)).toBe("<p>testX[]</p>");

        // Undo becomes available
        await waitFor(".btn[name='undo']:not(.disabled)");
        expect(".btn[name='undo']").not.toHaveClass("disabled");
        expect(".btn[name='redo']").toHaveClass("disabled");

        // Click on undo
        click(".btn[name='undo']");
        await animationFrame();
        expect(getContent(el)).toBe("<p>test[]</p>");

        // Redo becomes available, and undo disabled
        await waitFor(".btn[name='redo']:not(.disabled)");
        expect(".btn[name='undo']").toHaveClass("disabled");
        expect(".btn[name='redo']").not.toHaveClass("disabled");

        // Click on redo
        click(".btn[name='redo']");
        await animationFrame();
        expect(getContent(el)).toBe("<p>testX[]</p>");

        // Same state as before (can undo, cannot redo)
        await waitFor(".btn[name='undo']:not(.disabled)");
        expect(".btn[name='undo']").not.toHaveClass("disabled");
        expect(".btn[name='redo']").toHaveClass("disabled");
    });
});

test("toolbar update should be run only once", async () => {
    let counter = 0;
    patchWithCleanup(ToolbarPlugin.prototype, {
        _updateToolbar(...args) {
            super._updateToolbar(...args);
            counter++;
        },
    });
    const { el } = await setupEditor("<p>[test]</p>");
    await waitFor(".o-we-toolbar");
    counter = 0;
    click(".o-we-toolbar .btn[name='bold']");
    await animationFrame();
    expect(getContent(el)).toBe("<p><strong>[test]</strong></p>");
    expect(counter).toBe(1);
});

test("toolbar strikethrough buttons should not be active when checked list is strikethrough using o_checked class", async () => {
    const { el } = await setupEditor(
        '<ul class="o_checklist"><li class="o_checked">[test]</li></ul>'
    );
    await expandToolbar();
    expect(".o-we-toolbar .btn[name='strikethrough']").toHaveCount(1);
    expect(".o-we-toolbar .btn[name='strikethrough']").not.toHaveClass("active");
    await contains(".o-we-toolbar .btn[name='strikethrough']").click();
    await waitFor(".btn[name='strikethrough'].active");
    expect(getContent(el)).toBe(
        '<ul class="o_checklist"><li class="o_checked"><s>[test]</s></li></ul>'
    );
    expect(".o-we-toolbar .btn[name='strikethrough']").toHaveClass("active");
    await contains(".o-we-toolbar .btn[name='strikethrough']").click();
    await waitFor(".btn[name='strikethrough']:not(.active)");
    expect(getContent(el)).toBe('<ul class="o_checklist"><li class="o_checked">[test]</li></ul>');
    expect(".o-we-toolbar .btn[name='strikethrough']").not.toHaveClass("active");
});

test.tags("desktop");
test("dropdown menu should not overflow scroll container", async () => {
    class Test extends models.Model {
        name = fields.Char();
        txt = fields.Html();
        _records = [{ id: 1, name: "Test", txt: "<p>text</p>".repeat(50) }];
    }

    defineModels([Test]);
    await mountView({
        type: "form",
        resId: 1,
        resModel: "test",
        arch: `
            <form>
                <field name="name"/>
                <field name="txt" widget="html"/>
            </form>`,
    });

    const top = (rangeOrElement) => rangeOrElement.getBoundingClientRect().top;
    const bottom = (elementOrRange) => elementOrRange.getBoundingClientRect().bottom;
    const scrollableElement = queryOne(".o_content");
    const editable = queryOne(".odoo-editor-editable");

    // Select a paragraph in the middle of the text
    const fifthParagraph = editable.children[5];
    setSelection({
        anchorNode: fifthParagraph,
        anchorOffset: 0,
        focusNode: fifthParagraph,
        focusOffset: 1,
    });
    const range = document.getSelection().getRangeAt(0);

    await expandToolbar();
    const toolbar = queryOne(".o-we-toolbar");

    // Toolbar should be above the selection
    expect(bottom(toolbar)).toBeLessThan(top(range));

    // Color selector
    await contains(".o-we-toolbar .o-select-color-foreground").click();
    await expectElementCount(".o_font_color_selector", 1);
    const colorSelector = queryOne(".o_font_color_selector");

    // Scroll down to bring the toolbar close to the top
    let scrollStep = top(toolbar) - top(scrollableElement);
    scrollableElement.scrollTop += scrollStep;
    await animationFrame();

    // Toolbar should be below the selection
    expect(top(toolbar)).toBeGreaterThan(bottom(range));

    // Scroll down to make the toolbar overflow the scroll container
    scrollStep = top(toolbar) - top(scrollableElement);
    scrollableElement.scrollTop += scrollStep;
    await animationFrame();
    await advanceTime(200);

    // Toolbar should be invisible
    expect(toolbar).not.toBeVisible();

    // Color selector should be invisible
    expect(colorSelector).not.toBeVisible();

    // Scroll up to make toolbar visible
    scrollableElement.scrollTop = 0;
    await animationFrame();
    await advanceTime(200);
    expect(toolbar).toBeVisible();

    // Color selector should be visible along with toolbar
    expect(colorSelector).toBeVisible();

    // Font selector
    await contains(".o-we-toolbar [name='font'] .dropdown-toggle").click();
    await expectElementCount(".o_font_selector_menu", 1);
    const fontSelector = queryOne(".o_font_selector_menu");

    // Scroll down to make the toolbar overflow the scroll container
    scrollStep = top(toolbar) - top(scrollableElement);
    scrollableElement.scrollTop += scrollStep;
    await animationFrame();

    // Toolbar should be invisible
    expect(toolbar).not.toBeVisible();

    // Font selector should be invisible
    expect(fontSelector).not.toBeVisible();

    // Scroll up to make toolbar visible
    scrollableElement.scrollTop -= scrollStep;
    await animationFrame();
    expect(toolbar).toBeVisible();

    // Font selector should be visible
    expect(fontSelector).toBeVisible();
});

test.tags("desktop");
test("toolbar should not be displayed when only invisible nodes are selected", async () => {
    const { el } = await setupEditor(
        `<div><p>[abc]</p><h1 class="d-none">I'm not displayed</h1></div>`
    );
    await waitFor(".o-we-toolbar");
    await expectElementCount(".o-we-toolbar", 1);
    setContent(el, `<div><p>abc</p><h1 class="d-none">[I'm not displayed]</h1></div>`);
    await expectElementCount(".o-we-toolbar", 0);
});
