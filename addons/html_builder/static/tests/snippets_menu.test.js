import { unformat } from "@html_editor/../tests/_helpers/format";
import { setContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    queryAll,
    queryAllTexts,
    queryFirst,
    queryOne,
    waitFor,
} from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, openSnippetsMenu, setupWebsiteBuilder, getEditable } from "./helpers";

defineWebsiteModels();

function getSnippetStructure({ name, content, keywords = [], groupName }) {
    keywords = keywords.join(", ");
    return `<div name="${name}" data-oe-snippet-id="123" data-oe-keywords="${keywords}" data-o-group="${groupName}">${content}</div>`;
}

function getBasicSection(content) {
    return unformat(`<section class="s_test" data-snippet="s_test">
        <div class="test_a">${content}</div>
    </section>`);
}

test("open SnippetsMenu and discard", async () => {
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openSnippetsMenu();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(0);
    await click(".o-snippets-top-actions button:contains(Discard)");
    await animationFrame();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
});

test("navigate between builder tab don't fetch snippet description again", async () => {
    onRpc("render_public_asset", () => {
        expect.step("render_public_asset");
    });
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    await openSnippetsMenu();
    expect(queryAllTexts(".o-website-snippetsmenu .o-snippets-tabs span")).toEqual([
        "BLOCKS",
        "CUSTOMIZE",
        "THEME",
    ]);
    expect(queryOne(".o-website-snippetsmenu .o-snippets-tabs span.active")).toHaveText("BLOCKS");
    expect.verifySteps(["render_public_asset"]);

    await contains(".o-website-snippetsmenu .o-snippets-tabs span:contains(THEME)").click();
    expect(queryOne(".o-website-snippetsmenu .o-snippets-tabs span.active")).toHaveText("THEME");

    await contains(".o-website-snippetsmenu .o-snippets-tabs span:contains(BLOCK)").click();
    expect(queryOne(".o-website-snippetsmenu .o-snippets-tabs span.active")).toHaveText("BLOCKS");
    expect.verifySteps([]);
});

test("undo and redo buttons", async () => {
    const { getEditor } = await setupWebsiteBuilder(getEditable("<p> Text </p>"));
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openSnippetsMenu();
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    expect(":iframe #wrap").toHaveClass("o_editable");
    const editor = getEditor();
    setContent(
        editor.editable,
        getEditable(
            '<div id="wrap" class="o_editable" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"><p> Text[] </p></div>'
        )
    );
    await insertText(editor, "a");
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"> <div id="wrap" class="o_editable o_dirty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"> <p> Texta </p> </div> </div>'
    );
    await animationFrame();
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch" class="o_editable"> <p> Text </p> </div>'
    );
    await click(".o-snippets-menu button.fa-repeat");
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"> <div id="wrap" class="o_editable o_dirty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch"> <p> Texta </p> </div> </div>'
    );
});

test("display group snippet", async () => {
    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-o-image-preview="" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-oe-keywords="" data-o-snippet-group="a"><section class="s_snippet_group" data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-o-image-preview="" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-oe-keywords="" data-o-snippet-group="b"><section class="s_snippet_group" data-snippet="s_snippet_group"></section></div>',
                '<div name="C" data-o-image-preview="" data-oe-thumbnail="c.svg" data-oe-snippet-id="123" data-oe-keywords="" data-o-snippet-group="c"><section class="s_snippet_group" data-snippet="s_snippet_group"></section></div>',
            ],
        },
    });
    await openSnippetsMenu();
    const snippetGroupsSelector = `.o-snippets-menu [data-category="snippet_groups"]`;
    expect(snippetGroupsSelector).toHaveCount(3);
    expect(queryAllTexts(snippetGroupsSelector)).toEqual(["A", "B", "C"]);
    const imgSrc = queryAll(`${snippetGroupsSelector} img`).map((img) => img.dataset.src);
    expect(imgSrc).toEqual(["a.svg", "b.svg", "c.svg"]);
});

test("display inner content snippet", async () => {
    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_content: [
                `<div name="Button A" data-oe-thumbnail="buttonA.svg" data-oe-snippet-id="123">
                    <a class="btn btn-primary" href="#" data-snippet="s_button">Button A</a>
                </div>`,
                `<div name="Button B" data-oe-thumbnail="buttonB.svg" data-oe-snippet-id="123">
                    <a class="btn btn-primary" href="#" data-snippet="s_button">Button B</a>
                </div>`,
            ],
        },
    });
    await openSnippetsMenu();
    const snippetInnerContentSelector = `.o-snippets-menu [data-category="snippet_content"]`;
    expect(snippetInnerContentSelector).toHaveCount(2);
    expect(queryAllTexts(snippetInnerContentSelector)).toEqual(["Button A", "Button B"]);
    const imgSrc = queryAll(`${snippetInnerContentSelector} img`).map((img) => img.dataset.src);
    expect(imgSrc).toEqual(["buttonA.svg", "buttonB.svg"]);
});

test("open add snippet dialog + switch snippet category", async () => {
    const snippetsDescription = [
        {
            name: "Test",
            groupName: "a",
            content: getBasicSection("Yop"),
        },
        {
            name: "Test",
            groupName: "a",
            content: getBasicSection("Hello"),
        },
        {
            name: "Test",
            groupName: "b",
            content: getBasicSection("Nice"),
        },
    ];

    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-o-snippet-group="b"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription.map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    await openSnippetsMenu();
    expect(queryAllTexts(`.o-snippets-menu [data-category="snippet_groups"]`)).toEqual(["A", "B"]);

    await click(queryFirst(`.o-snippets-menu [data-category="snippet_groups"] div`));
    await waitFor(".o_add_snippet_dialog");
    expect(queryAllTexts(".o_add_snippet_dialog aside .list-group .list-group-item")).toEqual([
        "A",
        "B",
    ]);
    expect(".o_add_snippet_dialog aside .list-group .list-group-item.active").toHaveText("A");

    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe", { timeout: 500 });
    expect(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
    ).toHaveCount(2);
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(snippetsDescription.filter((s) => s.groupName === "a").map((s) => s.content));

    await click(".o_add_snippet_dialog aside .list-group .list-group-item:contains('B')");
    await animationFrame();
    expect(".o_add_snippet_dialog aside .list-group .list-group-item.active").toHaveText("B");
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(snippetsDescription.filter((s) => s.groupName === "b").map((s) => s.content));
});

test("drag & drop inner content block", async () => {
    const { getEditor } = await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_content: [
                `<div name="Button A" data-oe-thumbnail="buttonA.svg" data-oe-snippet-id="123">
                    <a class="btn btn-primary" href="#" data-snippet="s_button">Button A</a>
                </div>`,
                `<div name="Button B" data-oe-thumbnail="buttonB.svg" data-oe-snippet-id="123">
                    <a class="btn btn-primary" href="#" data-snippet="s_button">Button B</a>
                </div>`,
            ],
        },
    });
    await openSnippetsMenu();
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
        snippets: {
            snippet_content: [
                `<div name="Button A" data-oe-thumbnail="buttonA.svg" data-oe-snippet-id="123">
                    <a class="btn btn-primary" href="#" data-snippet="s_button">Button A</a>
                </div>`,
                `<div name="Button B" data-oe-thumbnail="buttonB.svg" data-oe-snippet-id="123">
                    <a class="btn btn-primary" href="#" data-snippet="s_button">Button B</a>
                </div>`,
            ],
        },
    });
    await openSnippetsMenu();
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
