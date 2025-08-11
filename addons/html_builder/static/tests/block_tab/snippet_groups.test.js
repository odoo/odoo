import { beforeEach, expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAll, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    addDropZoneSelector,
    createTestSnippets,
    getDragHelper,
    getSnippetStructure,
    setupHTMLBuilder,
    setupHTMLBuilderWithDummySnippet,
    waitForEndOfOperation,
    waitForSnippetDialog,
} from "../helpers";
import { Builder } from "@html_builder/builder";

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
    await setupHTMLBuilder("<div><p>Text</p></div>", {
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
    patchWithCleanup(Builder.prototype, {
        setup() {
            this.props.installSnippetModule = ({ moduleId }) => {
                expect(moduleId).toEqual("111");
                expect.step(`button_immediate_install`);
            };
            super.setup(...arguments);
        },
    });

    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-module-id="111" data-module-display-name="module_A" data-oe-thumbnail="a.svg"><section class="s_snippet_group" data-snippet="s_snippet_group"></section></div>',
            ],
        },
    });
    await click(`.o-snippets-menu #snippet_groups .o_snippet .btn.o_install_btn`);
    await animationFrame();

    expect(".modal").toHaveCount(1);
    expect(".modal-body").toHaveText(
        "Do you want to install module_A App?\nMore info about this app."
    );

    await contains(".modal .btn-primary:contains('Save and Install')").click();
    expect.verifySteps([`button_immediate_install`]);
});

test("install an app from snippet structure", async () => {
    patchWithCleanup(Builder.prototype, {
        setup() {
            this.props.installSnippetModule = ({ moduleId }) => {
                expect(moduleId).toEqual("111");
                expect.step(`button_immediate_install`);
            };
            super.setup(...arguments);
        },
    });

    const snippetsDescription = createTestSnippets({
        snippets: [
            {
                name: "Test 1",
                moduleDisplayName: "Test 1 module",
                groupName: "a",
                innerHTML: "Yop",
                moduleId: 111,
            },
            {
                name: "Test 2",
                moduleDisplayName: "Test 2 module",
                groupName: "a",
                innerHTML: "Hello",
            },
        ],
    });

    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsDescription.map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    await click(".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area");
    await waitForSnippetDialog();
    expect(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
    ).toHaveCount(2);
    expect(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap .o_snippet_preview_install_btn"
    ).toHaveCount(1);
    expect(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap:has(.o_snippet_preview_install_btn) .s_test"
    ).toHaveText("Yop");

    await click(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap .o_snippet_preview_install_btn"
    );
    await animationFrame();
    expect(".o_dialog:not(:has(.o_inactive_modal)) .modal-body").toHaveText(
        "Do you want to install Test 1 module App?\nMore info about this app."
    );
    await contains(
        ".o_dialog:not(:has(.o_inactive_modal)) .btn-primary:contains('Save and Install')"
    ).click();
    expect.verifySteps([`button_immediate_install`]);
});

test("open add snippet dialog + switch snippet category", async () => {
    const snippets = [
        { name: "Test", groupName: "a", innerHTML: "Yop" },
        { name: "Test", groupName: "a", innerHTML: "Hello" },
        { name: "Test", groupName: "b", innerHTML: "Nice" },
    ];

    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-o-snippet-group="b"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: createTestSnippets({ snippets, withName: false }).map(
                (snippetDesc) => getSnippetStructure(snippetDesc)
            ),
        },
    });
    expect(queryAllTexts(".o-snippets-menu #snippet_groups .o_snippet")).toEqual(["A", "B"]);
    await click(".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area");
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
        createTestSnippets({ snippets, withName: true })
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
        createTestSnippets({ snippets, withName: true })
            .filter((s) => s.groupName === "b")
            .map((s) => s.content)
    );
});

test("search snippet in add snippet dialog", async () => {
    const snippets = [
        { name: "gravy", groupName: "a", innerHTML: "content 1", keywords: ["jumper"] },
        { name: "bandage", groupName: "a", innerHTML: "content 2", keywords: ["order"] },
        {
            name: "banana",
            groupName: "b",
            innerHTML: "content 3",
            keywords: ["grape", "orange"],
        },
    ];

    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-o-snippet-group="b"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: createTestSnippets({ snippets, withName: false }).map(
                (snippetDesc) => getSnippetStructure(snippetDesc)
            ),
        },
    });
    await click(".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area");
    await waitForSnippetDialog();
    expect("aside .list-group .list-group-item").toHaveCount(2);
    const snippetsDescriptionProcessed = createTestSnippets({ snippets, withName: true });
    expect(
        queryAll(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap").map(
            (el) => el.innerHTML
        )
    ).toEqual(
        snippetsDescriptionProcessed.filter((s) => s.groupName === "a").map((s) => s.content)
    );

    // Search base on snippet name
    await contains(".o_add_snippet_dialog aside input[type='search']").edit("Ban");
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

test("search snippet by class", async () => {
    const snippets = [
        {
            name: "foo_bar",
            groupName: "a",
            innerHTML: "content 1",
            snippet: "s_foo_bar",
            additionalClassOnRoot: "s_additional_class",
            keywords: [],
        },
        // The second snippet includes a child class selector using innerHTML.
        // Using createTestSnippets with withName toggles the data-name automatically.
        {
            name: "foo",
            groupName: "a",
            innerHTML: `<div class="s_class_on_child">content 2</div>`,
            snippet: "s_foo",
            keywords: [],
        },
        {
            name: "bar",
            groupName: "a",
            innerHTML: "content 3",
            snippet: "s_bar",
            keywords: [],
        },
    ];

    const snippetsForSetup = createTestSnippets({ snippets, withName: false });
    const snippetsDescriptionProcessed = createTestSnippets({ snippets, withName: true });

    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: snippetsForSetup.map((snippetDesc) =>
                getSnippetStructure(snippetDesc)
            ),
        },
    });
    await click(".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area");
    await waitForSnippetDialog();

    // Search among classes of root node
    await contains(".o_add_snippet_dialog aside input[type='search']").edit("s_bar");
    expect(
        queryFirst(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap")
            .innerHTML
    ).toEqual(snippetsDescriptionProcessed[2].content);

    await contains(".o_add_snippet_dialog aside input[type='search']").edit("s_additional_class");
    expect(
        queryFirst(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap")
            .innerHTML
    ).toEqual(snippetsDescriptionProcessed[0].content);

    // Search among classes of child nodes
    await contains(".o_add_snippet_dialog aside input[type='search']").edit("s_class_on_child");
    expect(
        queryFirst(".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap")
            .innerHTML
    ).toEqual(snippetsDescriptionProcessed[1].content);
});

test("add snippet dialog with imagePreview", async () => {
    const snippets = [
        { name: "gravy", groupName: "a", innerHTML: "content 1" },
        { name: "banana", groupName: "a", innerHTML: "content 2", imagePreview: "banana.png" },
    ];

    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
                '<div name="B" data-oe-thumbnail="b.svg" data-oe-snippet-id="123" data-o-snippet-group="b"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: createTestSnippets({ snippets, withName: false }).map(
                (snippetDesc) => getSnippetStructure(snippetDesc)
            ),
        },
    });
    await click(".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area");
    const previewSnippetIframeSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    await waitForSnippetDialog();
    expect(`${previewSnippetIframeSelector}`).toHaveCount(2);
    const snippetsDescriptionProcessed = createTestSnippets({ snippets, withName: true });
    expect(`${previewSnippetIframeSelector}:first`).toHaveInnerHTML(
        snippetsDescriptionProcessed[0].content
    );
    expect(
        `${previewSnippetIframeSelector}:nth-child(1) .s_dialog_preview_image img`
    ).toHaveAttribute("data-src", snippetsDescriptionProcessed[1].imagePreview);
});

test("insert snippet structure", async () => {
    const snippets = [{ name: "Test", groupName: "a", innerHTML: "Yop" }];

    const { contentEl } = await setupHTMLBuilder("<section><p>Text</p></section>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: createTestSnippets({ snippets, withName: false }).map(
                (snippetDesc) => getSnippetStructure(snippetDesc)
            ),
        },
    });
    expect(contentEl).toHaveInnerHTML(`<section><p>Text</p></section>`);

    await click(".o-snippets-menu #snippet_groups .o_snippet_thumbnail .o_snippet_thumbnail_area");
    await waitForSnippetDialog();
    const previewSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    expect(previewSelector).toHaveCount(1);

    await contains(previewSelector).click();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(
        `<section><p>Text</p></section>${
            createTestSnippets({ snippets, withName: true })[0].content
        }`
    );
});

test("Drag & drop snippet structure", async () => {
    const snippets = [{ name: "Test", groupName: "a", innerHTML: "Yop" }];

    const { contentEl } = await setupHTMLBuilder("<section><p>Text</p></section>", {
        snippets: {
            snippet_groups: [
                '<div name="A" data-oe-thumbnail="a.svg" data-oe-snippet-id="123" data-o-snippet-group="a"><section data-snippet="s_snippet_group"></section></div>',
            ],
            snippet_structure: createTestSnippets({ snippets, withName: false }).map(
                (snippetDesc) => getSnippetStructure(snippetDesc)
            ),
        },
    });
    expect(contentEl).toHaveInnerHTML(`<section><p>Text</p></section>`);

    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .oe_drop_zone.o_dropzone_highlighted:nth-child(1)").toHaveCount(1);
    await drop(getDragHelper());
    expect(":iframe section[data-snippet='s_snippet_group']:nth-child(1)").toHaveCount(1);
    expect(".o_add_snippet_dialog").toHaveCount(1);

    await waitForSnippetDialog();
    const previewSelector =
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap";
    expect(previewSelector).toHaveCount(1);

    await contains(previewSelector).click();
    expect(".o_add_snippet_dialog").toHaveCount(0);
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(
        `${
            createTestSnippets({ snippets, withName: true })[0].content
        }<section><p>Text</p></section>`
    );
});

test("Cancel snippet drag & drop over sidebar", async () => {
    const { contentEl } = await setupHTMLBuilderWithDummySnippet();

    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone").toHaveCount(1);

    // Specifying an explicit target should not be needed, but the test
    // sometimes fails, probably because the snippet is partially touching the
    // iframe. We drop on the "Save" button to be as far as possible from the
    // iframe.
    await moveTo(".o-website-builder_sidebar button[data-action=save]");
    await drop(getDragHelper());
    expect(".o_add_snippet_dialog").toHaveCount(0);
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML("");
});

test("Renaming custom snippets don't make an orm call", async () => {
    // Stub rename_snippet RPC to succeed if it is called
    onRpc("ir.ui.view", "rename_snippet", ({ args }) => true);

    const customSnippets = createTestSnippets({
        snippets: [
            {
                name: "Dummy Section",
                groupName: "custom",
                keywords: ["dummy"],
                content: `
        <section data-snippet="s_dummy">
            <div class="container">
                <div class="row">
                    <div class="col-lg-7">
                        <p>TEST</p>
                    </div>
                </div>
            </div>
        </section>
    `,
            },
        ],
        withName: true,
    });
    const snippets = {
        snippet_groups: [
            '<div name="Custom" data-oe-snippet-id="123" data-o-snippet-group="custom"><section data-snippet="s_snippet_group"></section></div>',
        ],
        snippet_structure: customSnippets.map((snippetDesc) => getSnippetStructure(snippetDesc)),
        snippet_custom: customSnippets.map((snippetDesc) => getSnippetStructure(snippetDesc)),
    };

    await setupHTMLBuilder(
        `<section data-name="Dummy Section" data-snippet="s_dummy">
            <div class="container">
                <div class="row">
                    <div class="col-lg-7">
                        <p>TEST</p>
                        <p><a class="btn">BUTTON</a></p>
                    </div>
                </div>
            </div>
        </section>`,
        { snippets }
    );

    await contains(
        ".o-website-builder_sidebar .o_snippets_container .o_snippet[name='Custom'] button"
    ).click();
    await animationFrame();

    // Throw if any render_public_asset RPC happens during rename
    onRpc("ir.ui.view", "render_public_asset", () => {
        throw new Error("shouldn't make an rpc call on snippet rename");
    });

    await contains(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_custom_snippet_edit button.fa-pencil"
    ).click();
    expect(".o-overlay-item .modal-dialog:contains('Rename the block')").toHaveCount(1);
    await contains(".o-overlay-item .modal-dialog input#inputConfirmation").fill("new custom name");
    await contains(".o-overlay-item .modal-dialog footer>button:contains('Save')").click();
    expect(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_custom_snippet_edit>span:contains('new custom name')"
    ).toHaveCount(1);
});
