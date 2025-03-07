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
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    addDropZoneSelector,
    defineWebsiteModels,
    getSnippetStructure,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithDummySnippet,
    waitForSnippetDialog,
} from "../website_helpers";

defineWebsiteModels();

function getBasicSection(content, { name, withColoredLevelClass = false }) {
    const className = withColoredLevelClass ? "s_test o_colored_level" : "s_test";
    return unformat(`<section class="${className}" data-snippet="s_test" ${name ? `data-name="${name}"` : ""
        }>
        <div class="test_a o-paragraph">${content}</div>
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
    addDropZoneSelector({
        selector: "*",
        dropNear: "section",
    });
});

test("display group snippet", async () => {
    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets,
    });
    const snippetGroupsSelector = ".o-snippets-menu #snippet_groups .o_snippet";
    expect(snippetGroupsSelector).toHaveCount(3);
    expect(queryAllTexts(snippetGroupsSelector)).toEqual(["A", "B", "C"]);
    const thumbnailImgUrls = queryAll(`${snippetGroupsSelector} .o_snippet_thumbnail_img`).map(
        (thumbnail) => thumbnail.style.backgroundImage
    );
    expect(thumbnailImgUrls).toEqual(['url("a.svg")', 'url("b.svg")', 'url("c.svg")']);
});

test("install an app from snippet group", async () => {
    onRpc("ir.module.module", "button_immediate_install", ({ args }) => {
        expect(args[0]).toEqual([111]);
        expect.step(`button_immediate_install`);
        return true;
    });
    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-module-id="111" data-oe-thumbnail="a.svg"><section class="s_snippet_group" data-snippet="s_snippet_group"></section></div>',
            ],
        },
    });
    await click(`.o-snippets-menu #snippet_groups .o_snippet .btn.o_install_btn`);
    await animationFrame();
    expect(".modal").toHaveCount(1);
    expect(".modal-body").toHaveText("Do you want to install A App?\nMore info about this app.");

    await contains(".modal .btn-primary:contains('Save and Install')").click();
    expect.verifySteps([`button_immediate_install`]);
});

test("open add snippet dialog + switch snippet category", async () => {
    const snippetsDescription = (withName = false) => {
        const name = "Test";
        return [
            {
                name: name,
                groupName: "a",
                content: getBasicSection("Yop", { name: withName ? name : "" }),
            },
            {
                name: name,
                groupName: "a",
                content: getBasicSection("Hello", { name: withName ? name : "" }),
            },
            {
                name: name,
                groupName: "b",
                content: getBasicSection("Nice", { name: withName ? name : "" }),
            },
        ];
    };

    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-o-snippet-group="b"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription().map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    expect(queryAllTexts(".o-snippets-menu #snippet_groups .o_snippet")).toEqual(["A", "B"]);
    await click(
        queryFirst(
            ".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area"
        )
    );
    await waitForSnippetDialog();
    expect(queryAllTexts(".o_add_snippet_dialog aside .list-group .list-group-item")).toEqual([
        "A",
        "B",
    ]);
    expect(".o_add_snippet_dialog aside .list-group .list-group-item.active").toHaveText("A");

    expect(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
    ).toHaveCount(2);
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(
        snippetsDescription(true)
            .filter((s) => s.groupName === "a")
            .map((s) => s.content)
    );

    await click(".o_add_snippet_dialog aside .list-group .list-group-item:contains('B')");
    await animationFrame();
    expect(".o_add_snippet_dialog aside .list-group .list-group-item.active").toHaveText("B");
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(
        snippetsDescription(true)
            .filter((s) => s.groupName === "b")
            .map((s) => s.content)
    );
});

test("search snippet in add snippet dialog", async () => {
    const snippetsDescription = (withName = false) => {
        const name1 = "gravy";
        const name2 = "bandage";
        const name3 = "banana";
        return [
            {
                name: name1,
                groupName: "a",
                content: getBasicSection("content 1", { name: withName ? name1 : "" }),
                keywords: ["jumper"],
            },
            {
                name: name2,
                groupName: "a",
                content: getBasicSection("content 2", { name: withName ? name2 : "" }),
                keywords: ["order"],
            },
            {
                name: name3,
                groupName: "b",
                content: getBasicSection("content 3", { name: withName ? name3 : "" }),
                keywords: ["grape", "orange"],
            },
        ];
    };

    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-o-snippet-group="b"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription().map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    await click(
        queryFirst(
            ".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area"
        )
    );
    await waitForSnippetDialog();
    expect("aside .list-group .list-group-item").toHaveCount(2);
    const snippetsDescriptionProcessed = snippetsDescription(true);
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(
        snippetsDescriptionProcessed.filter((s) => s.groupName === "a").map((s) => s.content)
    );

    // Search base on snippet name
    await contains(".o_add_snippet_dialog aside input[type='search']").edit("ban");
    expect("aside .list-group .list-group-item").toHaveCount(0);
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(
        [snippetsDescriptionProcessed[1], snippetsDescriptionProcessed[2]].map((s) => s.content)
    );

    // Search base on snippet name and keywords
    await contains(".o_add_snippet_dialog aside input[type='search']").edit("gra");
    expect("aside .list-group .list-group-item").toHaveCount(0);
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(
        [snippetsDescriptionProcessed[0], snippetsDescriptionProcessed[2]].map((s) => s.content)
    );

    // Search base on keywords
    await contains(".o_add_snippet_dialog aside input[type='search']").edit("or");
    expect("aside .list-group .list-group-item").toHaveCount(0);
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(
        [snippetsDescriptionProcessed[1], snippetsDescriptionProcessed[2]].map((s) => s.content)
    );
});

test("add snippet dialog with imagePreview", async () => {
    const snippetsDescription = (withName = false) => {
        const name1 = "gravy";
        const name2 = "banana";
        return [
            {
                name: name1,
                groupName: "a",
                content: getBasicSection("content 1", { name: withName ? name1 : "" }),
            },
            {
                name: name2,
                groupName: "a",
                content: getBasicSection("content 2", { name: withName ? name2 : "" }),
                imagePreview: "banana.png",
            },
        ];
    };

    await setupWebsiteBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-o-snippet-group="b"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription().map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    await click(
        queryFirst(
            ".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area"
        )
    );
    const previewSnippetIframeSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    await waitForSnippetDialog();
    expect(`${previewSnippetIframeSelector}`).toHaveCount(2);
    const snippetsDescriptionProcessed = snippetsDescription(true);
    expect(`${previewSnippetIframeSelector}:first`).toHaveInnerHTML(
        snippetsDescriptionProcessed[0].content
    );
    expect(
        `${previewSnippetIframeSelector}:nth-child(1) .s_dialog_preview_image img`
    ).toHaveAttribute("data-src", snippetsDescriptionProcessed[1].imagePreview);
});

test("insert snippet structure", async () => {
    const snippetsDescription = ({ withName, withColoredLevelClass = false }) => {
        const name = "Test";
        return [
            {
                name: name,
                groupName: "a",
                content: getBasicSection("Yop", {
                    name: withName ? name : "",
                    withColoredLevelClass: withColoredLevelClass,
                }),
            },
        ];
    };

    const { getEditableContent } = await setupWebsiteBuilder("<section><p>Text</p></section>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription({ withName: false }).map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    const editableContent = getEditableContent();
    expect(editableContent).toHaveInnerHTML(
        `<section class="o_colored_level"><p>Text</p></section>`
    );

    await click(
        queryFirst(
            ".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area"
        )
    );
    await waitForSnippetDialog();
    const previewSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    expect(previewSelector).toHaveCount(1);

    await contains(previewSelector).click();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(
        `<section class="o_colored_level"><p>Text</p></section>${snippetsDescription({ withName: true, withColoredLevelClass: true })[0].content
        }`
    );
});

test("drag&drop snippet structure", async () => {
    const snippetsDescription = ({ withName, withColoredLevelClass = false }) => {
        const name = "Test";
        return [
            {
                name: name,
                groupName: "a",
                content: getBasicSection("Yop", {
                    name: withName ? name : "",
                    withColoredLevelClass: withColoredLevelClass,
                }),
            },
        ];
    };

    const { getEditableContent } = await setupWebsiteBuilder("<section><p>Text</p></section>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription({ withName: false }).map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    const editableContent = getEditableContent();
    expect(editableContent).toHaveInnerHTML(
        `<section class="o_colored_level"><p>Text</p></section>`
    );

    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(editableContent.querySelector(".oe_drop_zone"));
    expect(":iframe .oe_drop_zone.o_dropzone_highlighted:nth-child(1)").toHaveCount(1);
    await drop();
    expect(".o_add_snippet_dialog").toHaveCount(1);
    expect(editableContent).toHaveInnerHTML(
        unformat(`<section class="o_colored_level"><p>Text</p></section>`)
    );

    await waitForSnippetDialog();
    const previewSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    expect(previewSelector).toHaveCount(1);

    await contains(previewSelector).click();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML(
        `${snippetsDescription({ withName: true, withColoredLevelClass: true })[0].content
        }<section class="o_colored_level"><p>Text</p></section>`
    );
});

test("cancel snippet drag & drop over sidebar", async () => {
    const { getEditableContent } = await setupWebsiteBuilderWithDummySnippet();
    const editableContent = getEditableContent();

    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone").toHaveCount(1);

    await moveTo(".o-website-builder_sidebar");
    // Specifying an explicit target should not be needed, but the test
    // sometimes fails, probably because the snippet is partially touching the
    // iframe. We drop on the "Save" button to be as far as possible from the
    // iframe.
    await drop("button[data-action=save]");
    expect(".o_add_snippet_dialog").toHaveCount(0);
    expect(editableContent).toHaveInnerHTML("");
});
