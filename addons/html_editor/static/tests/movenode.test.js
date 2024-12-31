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
    const moveElements = [...document.querySelectorAll(".oe-sidewidget-move")];
    expect(moveElements).toHaveLength(1);
    const elementRect = moveElements[0].getBoundingClientRect();
    expect(elementRect.top).toBe(0);
    expect(elementRect.left).toBe(5);
});
test("should show the hook when hovering the second P", async () => {
    const { el } = await setupEditor("<p>a[]</p><p>b</p>", {
        styleContent: styles,
    });
    await hover(el.querySelector("p:last-child"));
    const moveElements = [...document.querySelectorAll(".oe-sidewidget-move")];
    expect(moveElements).toHaveLength(1);
    const elementRect = moveElements[0].getBoundingClientRect();
    expect(elementRect.top).toBe(37);
    expect(elementRect.left).toBe(5);
});
test("should not show the hook when hovering a DIV which is not a baseContainer", async () => {
    const { el } = await setupEditor(`<p>a[]</p><div class="oe_unbreakable"><br></div><p>b</p>`, {
        styleContent: styles,
    });
    await hover(el.querySelector("div"));
    const moveElements = [...document.querySelectorAll(".oe-sidewidget-move")];
    expect(moveElements).toHaveLength(0);
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
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(8);
        await handle.moveTo(dropzones[0]);
        await handle.drop();
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
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(8);
        await handle.moveTo(dropzones[1]);
        await handle.drop();
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
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(8);
        await handle.moveTo(dropzones[2]);
        await handle.drop();
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
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(8);
        await handle.moveTo(dropzones[3]);
        await handle.drop();
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
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(8);
        const outsideArea = document.createElement("div");
        getFixture().appendChild(outsideArea);
        await handle.moveTo(outsideArea);
        await handle.drop();
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
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(8);
        handle.moveTo(dropzones[3]);
        const outsideArea = document.createElement("div");
        getFixture().appendChild(outsideArea);
        await handle.moveTo(outsideArea);
        await handle.drop();
        expect(getContent(el)).toBe(
            `<p>a[]</p><div class="oe_unbreakable"><br></div><div class="o-paragraph">d</div><p>b</p><p>c</p>`
        );
    });
});
