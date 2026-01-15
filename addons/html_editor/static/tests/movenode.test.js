import { describe, expect, getFixture, test } from "@odoo/hoot";
import { hover, click } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { contains } from "@web/../tests/web_test_helpers";
import { base64Img, setupEditor } from "./_helpers/editor";
import { getContent } from "./_helpers/selection";
import { unformat } from "./_helpers/format";
import { expectElementCount } from "./_helpers/ui_expectations";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { captionEmbedding } from "@html_editor/others/embedded_components/backend/caption/caption";

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
test("should show the hook when hovering a figure element", async () => {
    const { el } = await setupEditor(
        `<figure>
            <img class="img-fluid test-image" src="${base64Img}">
            <figcaption>Hello</figcaption>
        </figure>`,
        {
            config: {
                Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
                resources: {
                    embedded_components: [captionEmbedding],
                },
            },
            styleContent: styles,
        }
    );
    await hover(el.querySelector("figure"));
    expect(".oe-sidewidget-move").toHaveCount(1);
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
            `<p data-selection-placeholder=""><br></p><div class="oe_unbreakable"><br></div><p>a[]</p><div class="o-paragraph">d</div><p>b</p><p>c</p>`
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
            `<p data-selection-placeholder=""><br></p><div class="oe_unbreakable"><br></div><div class="o-paragraph">d</div><p>a[]</p><p>b</p><p>c</p>`
        );
    });
    test("should drop LI at correct position within list", async () => {
        const { el } = await setupEditor(`<ol><li>a[]</li><li>b</li><li>c</li><li>d</li></ol>`, {
            styleContent: styles,
        });
        await animationFrame();
        const firstLI = el.querySelector("li");
        await hover(firstLI);
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(8);
        await handle.moveTo(dropzones[5]);
        await handle.drop();
        expect(getContent(el)).toBe(`<ol><li>b</li><li>c</li><li>a[]</li><li>d</li></ol>`);
    });
    test("should drop LI from bulleted list to checklist at correct position", async () => {
        const { el } = await setupEditor(
            `<ul><li>a[]</li><li>b</li><li>c</li><li>d</li></ul><p>p</p><ul class="o_checklist"><li>One</li><li>Two</li></ul>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstLI = el.querySelector("li");
        await hover(firstLI);
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(14);
        await handle.moveTo(dropzones[11]);
        await handle.drop();
        expect(getContent(el)).toBe(
            `<ul><li>b</li><li>c</li><li>d</li></ul><p>p</p><ul class="o_checklist"><li>One</li><li>a[]</li><li>Two</li></ul>`
        );
    });
    test("should wrap LI in new UL or OL when moved outside existing list", async () => {
        const { el } = await setupEditor(
            `<ul class="o_checklist"><li>a[]</li><li>b</li><li>c</li><li>d</li></ul><p>e</p>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstLI = el.querySelector("li");
        await hover(firstLI);
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(10);
        await handle.moveTo(dropzones[9]);
        await handle.drop();
        expect(getContent(el)).toBe(
            `<ul class="o_checklist"><li>b</li><li>c</li><li>d</li></ul><p>e</p><ul class="o_checklist"><li>a</li>[]</ul>`
        );
    });
    test("should wrap non-LI element in LI and insert it into list at correct position", async () => {
        const { el } = await setupEditor(
            `<ul class="o_checklist"><li>a[]</li><li>b</li><li>c</li><li>d</li></ul><p>e</p>`,
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const p = el.querySelector("p");
        await hover(p);
        const moveElement = document.querySelector(".oe-sidewidget-move");
        let dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(0);
        await tick();
        const handle = await contains(moveElement).drag();
        dropzones = [...document.querySelectorAll(".oe-dropzone-box-side")];
        expect(dropzones).toHaveLength(10);
        await handle.moveTo(dropzones[3]);
        await handle.drop();
        expect(getContent(el)).toBe(
            `<ul class="o_checklist"><li>a</li><li>b</li><li><p>e</p>[]</li><li>c</li><li>d</li></ul>`
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

describe("click", () => {
    test("should select the text when clicked on a hook", async () => {
        const { el } = await setupEditor(`<p>some text</p><p>[]other text</p>`, {
            styleContent: styles,
        });
        await animationFrame();
        const firstP = el.querySelector("p");
        await hover(firstP);
        await animationFrame();
        expect(".oe-sidewidget-move").toHaveCount(1);
        await click(".oe-sidewidget-move");
        await animationFrame();
        expect(getContent(el)).toBe(`<p>[some text]</p><p>other text</p>`);
        await expectElementCount(".o-we-toolbar", 1);
    });

    test("should select the table when clicked on a hook", async () => {
        const { el } = await setupEditor(
            unformat(`
                <table>
                    <tbody>
                        <tr>
                            <td><p>[]<br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p><br></p>
            `),
            {
                styleContent: styles,
            }
        );
        await animationFrame();
        const firstTable = el.querySelector("table");
        await hover(firstTable);
        await animationFrame();
        expect(".oe-sidewidget-move").toHaveCount(1);
        await click(".oe-sidewidget-move");
        await animationFrame();
        expect(getContent(el)).toBe(
            unformat(`
                <p data-selection-placeholder=""><br></p>
                <table class="o_selected_table">
                    <tbody>
                        <tr>
                            <td class="o_selected_td"><p>[<br></p></td>
                            <td class="o_selected_td"><p><br></p></td>
                            <td class="o_selected_td"><p>]<br></p></td>
                        </tr>
                    </tbody>
                </table>
                <p><br></p>
            `)
        );
        await expectElementCount(".o-we-toolbar", 1);
    });

    test("should select a non-editable element completely when clicked on a hook", async () => {
        const { el } = await setupEditor(
            unformat(
                `<p>abc</p><div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p>Some</p>
                        <p>text[]</p>
                    </div>
                </div><p>def</p>`
            ),
            { styleContent: styles }
        );
        await animationFrame();
        const banner = el.querySelector(".o_editor_banner");
        await hover(banner);
        await animationFrame();
        expect(".oe-sidewidget-move").toHaveCount(1);
        await click(".oe-sidewidget-move");
        await animationFrame();
        expect(getContent(el)).toBe(
            unformat(`
                <p>abc</p>[<div class="o_editor_banner user-select-none o-contenteditable-false lh-1 d-flex align-items-center alert alert-info pb-0 pt-3" data-oe-role="status" contenteditable="false" role="status">
                    <i class="o_editor_banner_icon mb-3 fst-normal" data-oe-aria-label="Banner Info" aria-label="Banner Info">💡</i>
                    <div class="o_editor_banner_content o-contenteditable-true w-100 px-3" contenteditable="true">
                        <p>Some</p>
                        <p>text</p>
                    </div>
                </div>]<p>def</p>
            `)
        );
        await expectElementCount(".o-we-toolbar", 1);
    });
});
