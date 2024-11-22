import { unformat } from "@html_editor/../tests/_helpers/format";
import { beforeEach, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    queryAll,
    queryAllTexts,
    queryFirst,
    waitFor,
} from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../helpers";

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

let snippets;
beforeEach(() => {
    snippets = {
        snippet_groups: [
            '<div name="A" data-o-image-preview="" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-oe-keywords="" data-o-snippet-group="a"><section class="s_snippet_group" data-snippet="s_snippet_group"></section></div>',
            '<div name="B" data-o-image-preview="" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-oe-keywords="" data-o-snippet-group="b"><section class="s_snippet_group" data-snippet="s_snippet_group"></section></div>',
            '<div name="C" data-o-image-preview="" data-oe-thumbnail="c.svg" data-oe-snippet-id="123" data-oe-keywords="" data-o-snippet-group="c"><section class="s_snippet_group" data-snippet="s_snippet_group"></section></div>',
        ],
    };
});

test("display group snippet", async () => {
    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets,
    });
    const snippetGroupsSelector = `.o-snippets-menu [data-category="snippet_groups"]`;
    expect(snippetGroupsSelector).toHaveCount(3);
    expect(queryAllTexts(snippetGroupsSelector)).toEqual(["A", "B", "C"]);
    const imgSrc = queryAll(`${snippetGroupsSelector} img`).map((img) => img.dataset.src);
    expect(imgSrc).toEqual(["a.svg", "b.svg", "c.svg"]);
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

test("insert snippet structure", async () => {
    const snippetsDescription = [
        {
            name: "Test",
            groupName: "a",
            content: getBasicSection("Yop"),
        },
    ];

    const { getEditor } = await setupWebsiteBuilder("<section><p>Text</p></section>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription.map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    const editor = getEditor();
    expect(editor.editable).toHaveInnerHTML(`<section><p>Text</p></section>`);

    await click(queryFirst(`.o-snippets-menu [data-category="snippet_groups"] div`));
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe", { timeout: 500 });
    const previewSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    expect(previewSelector).toHaveCount(1);

    await contains(previewSelector).click();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(editor.editable).toHaveInnerHTML(
        `<section><p>Text</p></section>${snippetsDescription[0].content}`
    );
});

test("drag&drop snippet structure", async () => {
    const snippetsDescription = [
        {
            name: "Test",
            groupName: "a",
            content: getBasicSection("Yop"),
        },
    ];

    const { getEditor } = await setupWebsiteBuilder("<section><p>Text</p></section>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription.map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    const editor = getEditor();
    expect(editor.editable).toHaveInnerHTML(`<section><p>Text</p></section>`);

    const { moveTo, drop } = await contains(
        `.o-snippets-menu [data-category="snippet_groups"] div`
    ).drag();
    expect(editor.editable).toHaveInnerHTML(
        unformat(`
        <div class="oe_drop_zone oe_insert"></div>
        <section><p>Text</p></section>
        <div class="oe_drop_zone oe_insert"></div>`)
    );

    await moveTo(editor.editable.querySelector(".oe_drop_zone"));
    expect(editor.editable).toHaveInnerHTML(
        unformat(`
        <div class="oe_drop_zone oe_insert o_dropzone_highlighted"></div>
        <section><p>Text</p></section>
        <div class="oe_drop_zone oe_insert"></div>`)
    );
    await drop();
    expect(".o_add_snippet_dialog").toHaveCount(1);
    expect(editor.editable).toHaveInnerHTML(unformat(`<section><p>Text</p></section>`));

    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe", { timeout: 500 });
    const previewSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    expect(previewSelector).toHaveCount(1);

    await contains(previewSelector).click();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(editor.editable).toHaveInnerHTML(
        `${snippetsDescription[0].content}<section><p>Text</p></section>`
    );
});
