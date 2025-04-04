import { expect, test } from "@odoo/hoot";
import { setupEditor } from "../_helpers/editor";
import { expandToolbar } from "../_helpers/toolbar";
import { queryAll, click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { getContent, setContent } from "../_helpers/selection";
import { unformat } from "../_helpers/format";

test("paint format button should be the second last one in the decoration button group", async () => {
    await setupEditor("<p>[abc]</p>");
    await expandToolbar();
    const formatButtons = queryAll(".o-we-toolbar .btn-group[name='decoration'] .btn");
    expect(formatButtons.at(-2)).toHaveAttribute("name", "paint_format");
});

test("should be able to copy and apply bold format using paint format button", async () => {
    const { el } = await setupEditor("<p><strong>[abc]</strong></p><p>test</p>");
    await expandToolbar();
    expect(".btn[name='paint_format']").toHaveAttribute("title", "Copy format");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    expect(".btn[name='paint_format']").toHaveAttribute("title", "Apply format");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveAttribute("title", "Copy format");
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe("<p><strong>abc</strong></p><p><strong>[test]</strong></p>");
});

test("should be able to copy and apply italic format using paint format button", async () => {
    const { el } = await setupEditor("<p><em>[abc]</em></p><p>test</p>");
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe("<p><em>abc</em></p><p><em>[test]</em></p>");
});

test("should be able to copy and apply strikeThrough format using paint format button", async () => {
    const { el } = await setupEditor("<p><s>[abc]</s></p><p>test</p>");
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe("<p><s>abc</s></p><p><s>[test]</s></p>");
});

test("should be able to copy and apply font-size format using paint format button", async () => {
    const { el } = await setupEditor(
        '<p><span style="font-size: 36px;">[abc]</span></p><p>test</p>'
    );
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        '<p><span style="font-size: 36px;">abc</span></p><p><span style="font-size: 36px;">[test]</span></p>'
    );
});

test("should be able to copy and apply font-size class format using paint format button", async () => {
    const { el } = await setupEditor('<p><span class="h1-fs">[abc]</span></p><p>test</p>');
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        '<p><span class="h1-fs">abc</span></p><p><span class="h1-fs">[test]</span></p>'
    );
});

test("should be able to copy and apply fontFamily using paint format button", async () => {
    const { el } = await setupEditor(
        '<p><span style="font-family: testFont;">[abc]</span></p><p>test</p>'
    );
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        '<p><span style="font-family: testFont;">abc</span></p><p><span style="font-family: testFont;">[test]</span></p>'
    );
});

test("should be able to copy and apply text and background colors using paint format button", async () => {
    const { el } = await setupEditor(
        '<p><font style="color: rgb(0, 0, 255); background-color: rgb(0, 255, 0);">[abc]</font></p><p>test</p>'
    );
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        unformat(
            `<p><font style="color: rgb(0, 0, 255); background-color: rgb(0, 255, 0);">abc</font></p>
            <p><font style="color: rgb(0, 0, 255); background-color: rgb(0, 255, 0);">[test]</font></p>`
        )
    );
});

test("should be able to copy and apply multiple formats using paint format button", async () => {
    const { el } = await setupEditor(
        '<p><span class="h1-fs"><em><strong><font style="color: rgb(0, 255, 255);background-color: rgb(255, 0, 255);">[abc]</font></strong></em></span></p><p>test</p>'
    );
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        unformat(
            `<p><span class="h1-fs"><em><strong><font style="color: rgb(0, 255, 255);background-color: rgb(255, 0, 255);">abc</font></strong></em></span></p>
            <p><span class="h1-fs"><em><strong><font style="color: rgb(0, 255, 255); background-color: rgb(255, 0, 255);">[test]</font></strong></em></span></p>`
        )
    );
});

test("should be able to copy and apply formats from a list item", async () => {
    const { el } = await setupEditor(
        '<ul><li class="h1-fs" style="color: rgb(0, 255, 0);">[abc]</li></ul><p>test</p>'
    );
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelector("p");
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        unformat(
            `<ul>
                <li class="h1-fs" style="color: rgb(0, 255, 0);">abc</li>
            </ul>
            <p><span class="h1-fs"><font style="color: rgb(0, 255, 0);">[test]</font></span></p>`
        )
    );
});

test("should not copy formats when selection has multiple inline elements", async () => {
    await setupEditor("<p><strong>[abc</strong><em>def]</em></p>");
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
});

test("should remove existing formats when applying copied formats", async () => {
    const { el } = await setupEditor(
        '<p><strong><font style="color: rgb(0, 255, 0);">[abc]</font></strong></p><p><u>test</u></p>'
    );
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        unformat(
            `<p><strong><font style="color: rgb(0, 255, 0);">abc</font></strong></p>
            <p><strong><font style="color: rgb(0, 255, 0);">[test]</font></strong></p>`
        )
    );
});

test("should not copy text-align when copying formats", async () => {
    const { el } = await setupEditor(
        '<p style="text-align: center;"><strong>[abc]</strong></p><p>test</p>'
    );
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        '<p style="text-align: center;"><strong>abc</strong></p><p><strong>[test]</strong></p>'
    );
});

test("should not remove existing text-align format when applying copied formats", async () => {
    const { el } = await setupEditor(
        '<p><strong>[abc]</strong></p><p style="text-align: center;">test</p>'
    );
    await expandToolbar();
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").toHaveClass("active");
    const testParagraph = el.querySelectorAll("p")[1];
    setContent(testParagraph, "[test]");
    await click(".btn[name='paint_format']");
    await animationFrame();
    expect(".btn[name='paint_format']").not.toHaveClass("active");
    expect(getContent(el)).toBe(
        '<p><strong>abc</strong></p><p style="text-align: center;"><strong>[test]</strong></p>'
    );
});
