import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

test("TopMenuVisibility option should appear without overTheContent", async () => {
    await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `<input type="hidden" class="o_page_option_data" autocomplete="off" name="header_visible">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header">
                    Menu Content
            </header>`,
    });
    await contains(":iframe #wrapwrap > header").click();
    await waitFor("[data-label='Header Position']");
    expect("[data-label='Header Position']").toBeVisible();
    await contains("[data-label='Header Position'] .dropdown").click();
    expect(".o-overlay-container [data-action-value='overTheContent']").not.toHaveCount();
});

test("TopMenuVisibility option should appear with overTheContent", async () => {
    await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_overlay">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header">
                    Menu Content
            </header>`,
    });
    await contains(":iframe #wrapwrap > header").click();
    await waitFor("[data-label='Header Position']");
    expect("[data-label='Header Position']").toBeVisible();
    await contains("[data-label='Header Position'] .dropdown").click();
    expect(".o-overlay-container [data-action-value='overTheContent']").toBeVisible();
});

test("page is not customisable, TopMenuVisibility option should not appear", async () => {
    await setupWebsiteBuilder("", {
        openEditor: true,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header">
                    Menu Content
            </header>`,
    });
    await contains(":iframe #wrapwrap > header").click();
    expect("[data-label='Header Position']").not.toHaveCount();
});

test("undo overTheContent visibility", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_overlay">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header" class="">
                    Menu Content
            </header>`,
    });
    const editor = getEditor();
    await contains(":iframe #wrapwrap > header").click();
    const precedentWrapwrap = queryOne(":iframe #wrapwrap").outerHTML;
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='overTheContent']").click();
    undo(editor);
    redo(editor);
    undo(editor);
    const modifiedWrapwrap = queryOne(":iframe #wrapwrap");
    expect(modifiedWrapwrap).toHaveOuterHTML(precedentWrapwrap);
});

test("undo and comeback to a custom overTheContent color", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_overlay">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_color">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header" class="">
                    Menu Content
            </header>`,
    });
    const editor = getEditor();
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='overTheContent']").click();
    await contains("[data-label='Background'].hb-row-sublevel-2 .o_we_color_preview").click();
    await contains("[data-color='600']").click();
    const precedentWrapwrap = queryOne(":iframe #wrapwrap").outerHTML;
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='regular']").click();
    undo(editor);
    redo(editor);
    undo(editor);
    const modifiedWrapwrap = queryOne(":iframe #wrapwrap");
    expect(modifiedWrapwrap).toHaveOuterHTML(precedentWrapwrap);
});

test("undo hidden and come back to regular", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_visible">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header">
                    Menu Content
            </header>`,
    });
    const editor = getEditor();
    await contains(":iframe #wrapwrap > header").click();
    const precedentWrapwrap = queryOne(":iframe #wrapwrap").outerHTML;
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='hidden']").click();
    undo(editor);
    const modifiedWrapwrap = queryOne(":iframe #wrapwrap");
    expect(modifiedWrapwrap).toHaveOuterHTML(precedentWrapwrap);
});

test("regular -> hidden -> regular", async () => {
    await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_visible">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header" class="">
                    Menu Content
            </header>`,
    });
    await contains(":iframe #wrapwrap > header").click();
    const precedentWrapwrap = queryOne(":iframe #wrapwrap").outerHTML;
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='hidden']").click();
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='regular']").click();
    const modifiedWrapwrap = queryOne(":iframe #wrapwrap");
    expect(modifiedWrapwrap).toHaveOuterHTML(precedentWrapwrap);
});
