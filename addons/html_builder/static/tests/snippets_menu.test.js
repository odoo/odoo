import { WebsiteBuilder } from "@website/client_actions/website_preview/website_builder_action";
import { setContent } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { animationFrame, click, queryAllTexts, queryOne, waitFor } from "@odoo/hoot-dom";
import { contains, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "./website_helpers";

defineWebsiteModels();

test("open BuilderSidebar and discard", async () => {
    let websiteBuilder;
    patchWithCleanup(WebsiteBuilder.prototype, {
        setup() {
            websiteBuilder = this;
            super.setup();
        },
    });
    const { openBuilderSidebar } = await setupWebsiteBuilder(`<h1> Homepage </h1>`, {
        openEditor: false,
    });
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openBuilderSidebar();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(0);
    await click(".o-snippets-top-actions button:contains(Discard)");
    await websiteBuilder.iframeLoaded;
    await animationFrame();
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
});

test("navigate between builder tab don't fetch snippet description again", async () => {
    onRpc("render_public_asset", () => {
        expect.step("render_public_asset");
    });
    await setupWebsiteBuilder(`<h1> Homepage </h1>`);
    expect(queryAllTexts(".o-website-builder_sidebar .o-snippets-tabs span")).toEqual([
        "BLOCKS",
        "CUSTOMIZE",
        "THEME",
    ]);
    expect(queryOne(".o-website-builder_sidebar .o-snippets-tabs button.active")).toHaveText(
        "BLOCKS"
    );
    expect.verifySteps(["render_public_asset"]);

    await contains(".o-website-builder_sidebar .o-snippets-tabs span:contains(THEME)").click();
    await animationFrame();
    expect(queryOne(".o-website-builder_sidebar .o-snippets-tabs button.active")).toHaveText(
        "THEME"
    );

    await contains(".o-website-builder_sidebar .o-snippets-tabs span:contains(BLOCK)").click();
    expect(queryOne(".o-website-builder_sidebar .o-snippets-tabs button.active")).toHaveText(
        "BLOCKS"
    );
    expect.verifySteps([]);
});

test("undo and redo buttons", async () => {
    const { getEditor, getEditableContent, openBuilderSidebar } = await setupWebsiteBuilder(
        "<p> Text </p>",
        {
            openEditor: false,
        }
    );
    expect(".o_menu_systray .o-website-btn-custo-primary").toHaveCount(1);
    await openBuilderSidebar();
    expect(":iframe #wrap").not.toHaveClass("o_dirty");
    expect(":iframe #wrap").toHaveClass("o_editable");
    const editor = getEditor();
    const editableContent = getEditableContent();
    setContent(editableContent, "<p> Text[] </p>");
    await insertText(editor, "a");
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" class="oe_structure oe_empty o_editable o_dirty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch" data-editor-message-default="true" data-editor-message="DRAG BUILDING BLOCKS HERE" contenteditable="true"> <p> Texta </p> </div>'
    );
    await animationFrame();
    await click(".o-snippets-menu button.fa-undo");
    await animationFrame();
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" class="oe_structure oe_empty o_editable" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch" data-editor-message-default="true" data-editor-message="DRAG BUILDING BLOCKS HERE" contenteditable="true"> <p> Text </p> </div>'
    );
    await click(".o-snippets-menu button.fa-repeat");
    expect(editor.editable).toHaveInnerHTML(
        '<div id="wrap" class="oe_structure oe_empty o_editable o_dirty" data-oe-model="ir.ui.view" data-oe-id="539" data-oe-field="arch" data-editor-message-default="true" data-editor-message="DRAG BUILDING BLOCKS HERE" contenteditable="true"> <p> Texta </p> </div>'
    );
});

test("activate customize tab without any selection", async () => {
    await setupWebsiteBuilder("<h1> Homepage </h1>");
    expect(queryOne(".o-website-builder_sidebar .o-snippets-tabs button.active")).toHaveText(
        "BLOCKS"
    );
    await contains(
        ".o-website-builder_sidebar .o-snippets-tabs button:contains(CUSTOMIZE)"
    ).click();
    expect(queryOne(".o-website-builder_sidebar .o-snippets-tabs button.active")).toHaveText(
        "CUSTOMIZE"
    );
});

test("Clicking on the 'BLOCKS' or 'THEME' tab should deactivate the options", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner");

    await contains(":iframe .s_banner").click();
    await animationFrame();
    expect(".oe_overlay").toHaveCount(1);
    expect(".o-snippets-tabs button:contains('CUSTOMIZE')").toHaveClass("active");
    expect(".o_customize_tab .options-container").toHaveCount(1);

    await contains(".o-snippets-tabs button:contains('BLOCKS')").click();
    expect(".oe_overlay").toHaveCount(0);
    await contains(".o-snippets-tabs button:contains('CUSTOMIZE')").click();
    expect(".o-snippets-tabs button:contains('CUSTOMIZE')").toHaveClass("active");
    expect(".o_customize_tab .options-container").toHaveCount(0);

    await contains(":iframe .s_banner").click();
    await waitFor(".o_customize_tab .options-container");
    expect(".oe_overlay").toHaveCount(1);
    expect(".o-snippets-tabs button:contains('CUSTOMIZE')").toHaveClass("active");
    expect(".o_customize_tab .options-container").toHaveCount(1);

    await contains(".o-snippets-tabs button:contains('THEME')").click();
    expect(".oe_overlay").toHaveCount(0);
    await contains(".o-snippets-tabs button:contains('CUSTOMIZE')").click();
    expect(".o-snippets-tabs button:contains('CUSTOMIZE')").toHaveClass("active");
    expect(".o_customize_tab .options-container").toHaveCount(0);
});
