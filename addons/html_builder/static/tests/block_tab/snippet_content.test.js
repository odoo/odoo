import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll, queryAllTexts } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../helpers";

defineWebsiteModels();

let snippets;
beforeEach(() => {
    snippets = {
        snippet_content: [
            `<div name="Button A" data-oe-thumbnail="buttonA.svg" data-oe-snippet-id="123">
                <a class="btn btn-primary" href="#" data-snippet="s_button">Button A</a>
            </div>`,
            `<div name="Button B" data-oe-thumbnail="buttonB.svg" data-oe-snippet-id="123">
                <a class="btn btn-primary" href="#" data-snippet="s_button">Button B</a>
            </div>`,
        ],
    };
});

test("display inner content snippet", async () => {
    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets,
    });
    const snippetInnerContentSelector = `.o-snippets-menu [data-category="snippet_content"]`;
    expect(snippetInnerContentSelector).toHaveCount(2);
    expect(queryAllTexts(snippetInnerContentSelector)).toEqual(["Button A", "Button B"]);
    const imgSrc = queryAll(`${snippetInnerContentSelector} img`).map((img) => img.dataset.src);
    expect(imgSrc).toEqual(["buttonA.svg", "buttonB.svg"]);
});

test("drag & drop inner content block", async () => {
    const { getEditor } = await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets,
    });
    const editor = getEditor();
    expect(editor.editable).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-snippetsmenu .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(".o-website-snippetsmenu [name='Button A']").drag();
    await animationFrame(); // TODO we should remove it maybe bug utils hoot
    expect(editor.editable).toHaveInnerHTML(
        `<div><div class="oe_drop_zone oe_insert"></div><p>Text</p><div class="oe_drop_zone oe_insert"></div></div>`
    );
    expect(".o-website-snippetsmenu .fa-undo").not.toBeEnabled();

    await moveTo(editor.editable.querySelector(".oe_drop_zone"));
    expect(editor.editable).toHaveInnerHTML(
        `<div><div class="oe_drop_zone oe_insert o_dropzone_highlighted"></div><p>Text</p><div class="oe_drop_zone oe_insert"></div></div>`
    );
    expect(".o-website-snippetsmenu .fa-undo").not.toBeEnabled();

    await drop(editor.editable.querySelector(".oe_drop_zone"));
    expect(editor.editable).toHaveInnerHTML(
        `<div>\ufeff<a class="btn btn-primary" href="#" data-snippet="s_button">\ufeffButton A\ufeff</a>\ufeff<p>Text</p></div>`
    );
    expect(".o-website-snippetsmenu .fa-undo").toBeEnabled();
});

test("drag & drop inner content block + undo/redo", async () => {
    const { getEditor } = await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets,
    });
    const editor = getEditor();
    expect(editor.editable).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-snippetsmenu .fa-undo").not.toBeEnabled();
    expect(".o-website-snippetsmenu .fa-repeat").not.toBeEnabled();

    const { drop } = await contains(".o-website-snippetsmenu [name='Button A']").drag();
    await drop(editor.editable.querySelector(".oe_drop_zone"));
    expect(editor.editable).toHaveInnerHTML(
        `<div>\ufeff<a class="btn btn-primary" href="#" data-snippet="s_button">\ufeffButton A\ufeff</a>\ufeff<p>Text</p></div>`
    );
    expect(".o-website-snippetsmenu .fa-undo").toBeEnabled();
    expect(".o-website-snippetsmenu .fa-repeat").not.toBeEnabled();

    await click(".o-website-snippetsmenu .fa-undo");
    await animationFrame();
    expect(editor.editable).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-snippetsmenu .fa-undo").not.toBeEnabled();
    expect(".o-website-snippetsmenu .fa-repeat").toBeEnabled();
});
