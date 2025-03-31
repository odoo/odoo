import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";
import { undo, redo } from "@html_editor/../tests/_helpers/user_actions";
import { animationFrame, queryOne } from "@odoo/hoot-dom";

defineWebsiteModels();

test("TopMenuVisibility option should appear", async () => {
    await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `<input type="hidden" class="o_page_option_data" autocomplete="off" data-oe-model="ir.ui.view" data-oe-id="543" data-oe-field="arch" data-oe-xpath="/data/xpath[13]/t[1]/t[1]/input[1]" name="header_visible" value="True">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header">   
                    Menu Content
            </header>`,
    });
    await contains(":iframe #wrapwrap > header").click();
    await animationFrame();
    expect("[data-label='Header Position']").toBeVisible();
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
    expect("[data-label='Header Position']").not.toBeVisible();
});

test("undo overTheContent visibility", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `<input type="hidden" class="o_page_option_data" autocomplete="off" data-oe-model="ir.ui.view" data-oe-id="543" data-oe-field="arch" data-oe-xpath="/data/xpath[13]/t[1]/t[1]/input[1]" name="header_visible" value="True">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header" class="">   
                    Menu Content
            </header>`,
    });
    const editor = getEditor();
    await contains(":iframe #wrapwrap > header").click();
    const precedentWrapwrap = queryOne(":iframe #wrapwrap").outerHTML;
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains("[data-action-value='overTheContent']").click();
    undo(editor);
    redo(editor);
    undo(editor);
    const modifiedWrapwrap = queryOne(":iframe #wrapwrap");
    expect(modifiedWrapwrap).toHaveOuterHTML(precedentWrapwrap);
});

test("undo and comeback to a custom overTheContent color", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `<input type="hidden" class="o_page_option_data" autocomplete="off" data-oe-model="ir.ui.view" data-oe-id="543" data-oe-field="arch" data-oe-xpath="/data/xpath[13]/t[1]/t[1]/input[1]" name="header_visible" value="True">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header" class="">   
                    Menu Content
            </header>`,
    });
    const editor = getEditor();
    await contains(":iframe #wrapwrap > header").click();
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains("[data-action-value='overTheContent']").click();
    await contains("[data-label='Background'] .o_we_color_preview").click();
    await contains("[data-color='#0000FF']").click();
    const precedentWrapwrap = queryOne(":iframe #wrapwrap").outerHTML;
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains("[data-action-value='regular']").click();
    undo(editor);
    redo(editor);
    undo(editor);
    const modifiedWrapwrap = queryOne(":iframe #wrapwrap");
    expect(modifiedWrapwrap).toHaveOuterHTML(precedentWrapwrap);
});

test("undo hidden and come back to regular", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `<input type="hidden" class="o_page_option_data" autocomplete="off" data-oe-model="ir.ui.view" data-oe-id="543" data-oe-field="arch" data-oe-xpath="/data/xpath[13]/t[1]/t[1]/input[1]" name="header_visible" value="True">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header" class="">   
                    Menu Content
            </header>`,
    });
    const editor = getEditor();
    await contains(":iframe #wrapwrap > header").click();
    const precedentWrapwrap = queryOne(":iframe #wrapwrap").outerHTML;
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains("[data-action-value='hidden']").click();
    undo(editor);
    const modifiedWrapwrap = queryOne(":iframe #wrapwrap");
    expect(modifiedWrapwrap).toHaveOuterHTML(precedentWrapwrap);
});

test("regular -> hidden -> regular", async () => {
    await setupWebsiteBuilder("", {
        openEditor: true,
        beforeWrapwrapContent: `<input type="hidden" class="o_page_option_data" autocomplete="off" data-oe-model="ir.ui.view" data-oe-id="543" data-oe-field="arch" data-oe-xpath="/data/xpath[13]/t[1]/t[1]/input[1]" name="header_visible" value="True">`,
        headerContent: `
            <header id="top" data-anchor="true" data-name="Header" class="">   
                    Menu Content
            </header>`,
    });
    await contains(":iframe #wrapwrap > header").click();
    const precedentWrapwrap = queryOne(":iframe #wrapwrap").outerHTML;
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains("[data-action-value='hidden']").click();
    await contains("[data-label='Header Position'] .dropdown").click();
    await contains("[data-action-value='regular']").click();
    const modifiedWrapwrap = queryOne(":iframe #wrapwrap");
    expect(modifiedWrapwrap).toHaveOuterHTML(precedentWrapwrap);
});
