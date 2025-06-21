import { describe, expect, getFixture, test } from "@odoo/hoot";
import { hover } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";

describe.current.tags("desktop");

const styles = `
.odoo-editor-editable {
    position: fixed;
    top: 0;
    left: 30px;
    width: 100px;
}
`;

test("should show the hook when hovering a P", async () => {
    const { el } = await setupEditor("<p>a[]</p><p>b</p>", {
        styleContent: styles,
    });
    await hover(el.querySelector("p"));
    expect(".oe-sidewidget-move").toHaveCount(1);
    expect(".oe-sidewidget-move").toHaveRect({ top: 0, left: 5 });
});
test("should show the hook when hovering the second P", async () => {
    const { el } = await setupEditor("<p>a[]</p><p>b</p>", {
        styleContent: styles,
    });
    await hover(el.querySelector("p:last-child"));
    expect(".oe-sidewidget-move").toHaveCount(1);
    expect(".oe-sidewidget-move").toHaveRect({ top: 37, left: 5 });
});
test("should not show the hook when hovering a DIV which is not a baseContainer", async () => {
    const { el } = await setupEditor(`<p>a[]</p><div class="oe_unbreakable"><br></div><p>b</p>`, {
        styleContent: styles,
    });
    await hover(el.querySelector("div"));
    expect(".oe-sidewidget-move").toHaveCount(0);
});
describe("drag", () => {
    test("should drop at the same place before the same element", async () => {
        const { el } = await setupEditor(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div>d</div><p>b</p><p>c</p>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstP = el.querySelector("p");
        await hover(firstP);
        expect(".oe-dropzone-box-side").toHaveCount(0);
        await tick();
        const { drop } = await contains(".oe-sidewidget-move").drag();
        expect(".oe-dropzone-box-side").toHaveCount(8);
        await drop(".oe-dropzone-box-side:eq(0)");
        expect(getContent(el)).toBe(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div class="o-paragraph">d</div><p>b</p><p>c</p>`
        );
    });
    test("should drop at the same place after the same element", async () => {
        const { el } = await setupEditor(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div>d</div><p>b</p><p>c</p>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstP = el.querySelector("p");
        await hover(firstP);
        expect(".oe-dropzone-box-side").toHaveCount(0);
        await tick();
        const { drop } = await contains(".oe-sidewidget-move").drag();
        expect(".oe-dropzone-box-side").toHaveCount(8);
        await drop(".oe-dropzone-box-side:eq(1)");
        expect(getContent(el)).toBe(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div class="o-paragraph">d</div><p>b</p><p>c</p>`
        );
    });
    test("should drop before the next baseContainer", async () => {
        const { el } = await setupEditor(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div>d</div><p>b</p><p>c</p>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstP = el.querySelector("p");
        await hover(firstP);
        expect(".oe-dropzone-box-side").toHaveCount(0);
        await tick();
        const { drop } = await contains(".oe-sidewidget-move").drag();
        expect(".oe-dropzone-box-side").toHaveCount(8);
        await drop(".oe-dropzone-box-side:eq(2)");
        expect(getContent(el)).toBe(
            `<div class="oe_unbreakable"><br></div><p>a[]</p><div class="o-paragraph">d</div><p>b</p><p>c</p>`
        );
    });
    test("should drop after the next baseContainer", async () => {
        const { el } = await setupEditor(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div>d</div><p>b</p><p>c</p>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstP = el.querySelector("p");
        await hover(firstP);
        expect(".oe-dropzone-box-side").toHaveCount(0);
        await tick();
        const { drop } = await contains(".oe-sidewidget-move").drag();
        expect(".oe-dropzone-box-side").toHaveCount(8);
        await drop(".oe-dropzone-box-side:eq(3)");
        expect(getContent(el)).toBe(
            `<div class="oe_unbreakable"><br></div><div class="o-paragraph">d</div><p>a[]</p><p>b</p><p>c</p>`
        );
    });
    test("should do nothing when dropping outside the editable", async () => {
        const { el } = await setupEditor(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div>d</div><p>b</p><p>c</p>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstP = el.querySelector("p");
        await hover(firstP);
        expect(".oe-dropzone-box-side").toHaveCount(0);
        await tick();
        const { drop } = await contains(".oe-sidewidget-move").drag();
        expect(".oe-dropzone-box-side").toHaveCount(8);
        const outsideArea = document.createElement("div");
        getFixture().appendChild(outsideArea);
        await drop(outsideArea);
        expect(getContent(el)).toBe(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div class="o-paragraph">d</div><p>b</p><p>c</p>`
        );
    });
    test("should do nothing when dropping outside the editable and after hovering a hook", async () => {
        const { el } = await setupEditor(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div>d</div><p>b</p><p>c</p>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstP = el.querySelector("p");
        await hover(firstP);
        expect(".oe-dropzone-box-side").toHaveCount(0);
        await tick();
        const { drop, moveTo } = await contains(".oe-sidewidget-move").drag();
        expect(".oe-dropzone-box-side").toHaveCount(8);
        await moveTo(".oe-dropzone-box-side:eq(3)");
        const outsideArea = document.createElement("div");
        getFixture().appendChild(outsideArea);
        await drop(outsideArea);
        expect(getContent(el)).toBe(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div class="o-paragraph">d</div><p>b</p><p>c</p>`
        );
    });
});
