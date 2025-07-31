import { describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    Deferred,
    queryAll,
    queryAllTexts,
    queryOne,
    waitFor,
} from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupHTMLBuilder, getDragHelper, waitForEndOfOperation } from "../helpers";
import { Operation } from "@html_builder/core/operation";
import { BuilderOptionsPlugin } from "@html_builder/core/builder_options_plugin";
import { loadBundle } from "@web/core/assets";

describe.current.tags("desktop");

const snippetContent = [
    `<div name="Button A" data-oe-thumbnail="buttonA.svg" data-oe-snippet-id="123">
        <a class="btn btn-primary" href="#" data-snippet="s_button">Button A</a>
    </div>`,
    `<div name="Button B" data-oe-thumbnail="buttonB.svg" data-oe-snippet-id="123">
        <a class="btn btn-primary" href="#" data-snippet="s_button">Button B</a>
    </div>`,
];

const dropzoneSelectors = [
    {
        selector: "*",
        dropNear: "p",
    },
];

test("Display inner content snippet", async () => {
    await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    const snippetInnerContentSelector = ".o-snippets-menu #snippet_content .o_snippet";
    expect(snippetInnerContentSelector).toHaveCount(2);
    expect(queryAllTexts(snippetInnerContentSelector)).toEqual(["Button A", "Button B"]);
    const thumbnailImgUrls = queryAll(
        `${snippetInnerContentSelector} .o_snippet_thumbnail_img`
    ).map((thumbnail) => thumbnail.style.backgroundImage);
    expect(thumbnailImgUrls).toEqual(['url("buttonA.svg")', 'url("buttonB.svg")']);
});

test("Drag & drop inner content block", async () => {
    const { contentEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button A'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await moveTo(":iframe .oe_drop_zone");
    expect(":iframe .oe_drop_zone.invisible:nth-child(1)").toHaveCount(1);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();

    await drop(getDragHelper());
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(
        `<div>\ufeff<a class="btn btn-primary" href="#" data-snippet="s_button" data-name="Button A">\ufeffButton A\ufeff</a>\ufeff<p>Text</p></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
});

test("Drag & drop inner content block + undo/redo", async () => {
    const { contentEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    expect(".o-website-builder_sidebar .fa-repeat").not.toBeEnabled();

    await click(".o-website-builder_sidebar .fa-undo");
    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button A'] .o_snippet_thumbnail"
    ).drag();
    await moveTo(":iframe .oe_drop_zone");
    await drop(getDragHelper());
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(
        `<div>\ufeff<a class="btn btn-primary" href="#" data-snippet="s_button" data-name="Button A">\ufeffButton A\ufeff</a>\ufeff<p>Text</p></div>`
    );
    expect(".o-website-builder_sidebar .fa-undo").toBeEnabled();
    expect(".o-website-builder_sidebar .fa-repeat").not.toBeEnabled();

    await click(".o-website-builder_sidebar .fa-undo");
    await animationFrame();
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
    expect(".o-website-builder_sidebar .fa-undo").not.toBeEnabled();
    expect(".o-website-builder_sidebar .fa-repeat").toBeEnabled();
});

test("Drag inner content and drop it outside of a dropzone", async () => {
    const { contentEl, builderEl } = await setupHTMLBuilder("<div><p>Text</p></div>", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);

    const { moveTo, drop } = await contains(
        ".o-website-builder_sidebar [name='Button A'] .o_snippet_thumbnail"
    ).drag();
    expect(":iframe .oe_drop_zone:nth-child(1)").toHaveCount(1);
    expect(":iframe .oe_drop_zone:nth-child(3)").toHaveCount(1);

    await moveTo(builderEl);
    await drop(getDragHelper());
    await waitForEndOfOperation();

    expect(contentEl).toHaveInnerHTML(`<div><p>Text</p></div>`);
});

test("A snippet should appear disabled if there is nowhere to drop it", async () => {
    const { contentEl } = await setupHTMLBuilder("", {
        snippetContent,
        dropzoneSelectors,
    });
    expect(contentEl).toHaveInnerHTML("");
    expect(".o_block_tab .o_snippet.o_disabled").toHaveCount(2);
});

test.tags("desktop");
test("click just after drop is redispatched in next operation", async () => {
    const nextDef = new Deferred();
    patchWithCleanup(Operation.prototype, {
        next(fn, ...args) {
            const originalFn = fn;
            fn = async () => {
                await originalFn();
                nextDef.resolve();
            };
            expect.step(`next${args[0]?.shouldInterceptClick ? " should intercept" : ""}`);
            const res = super.next(fn, ...args);
            return res;
        },
    });
    patchWithCleanup(BuilderOptionsPlugin.prototype, {
        async onClick(ev) {
            expect.step("onClick");
            super.onClick(ev);
        },
        updateContainers(...args) {
            expect.step("updateContainers");
            super.updateContainers(...args);
        },
    });
    await setupHTMLBuilder("", {
        styleContent: /*css*/ `
            .o_loading_screen {
                position: absolute;
                inset: 0;
            }
            section {
                height: 100%; /* to easily target */
            }`,
    });

    // TODO: the next lines replicate website's `insertCategorySnippet` helper.
    // It should be moved to html_builder.
    await contains(".o-snippets-menu #snippet_groups .o_snippet_thumbnail_area").click();
    await animationFrame();
    await loadBundle("html_builder.iframe_add_dialog", {
        targetDoc: queryOne("iframe.o_add_snippet_iframe").contentDocument,
        js: false,
    });
    await waitFor(".o_add_snippet_dialog iframe.show.o_add_snippet_iframe");
    await contains(
        ".o_add_snippet_dialog .o_add_snippet_iframe:iframe .o_snippet_preview_wrap"
    ).click();
    await animationFrame();
    expect.verifySteps(["next should intercept"]); // On snippet selected

    await waitFor(":iframe .o_loading_screen");
    await click(":iframe", { position: { x: 200, y: 50 }, relative: true });
    expect.verifySteps(["next"]); // On click
    await nextDef;
    expect.verifySteps(["updateContainers"]); // End of drop, on addStep()
    await animationFrame();
    expect.verifySteps(["onClick", "next", "updateContainers"]); // On click redispatched
    await animationFrame();
    expect(".o-snippets-tabs .o-hb-btn.active").toHaveText("Edit");
});
