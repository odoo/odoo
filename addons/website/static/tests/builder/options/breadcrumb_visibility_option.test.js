import { redo, undo } from "@html_editor/../tests/_helpers/user_actions";
import { expect, test } from "@odoo/hoot";
import { queryOne, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, setupWebsiteBuilder } from "../website_helpers";

defineWebsiteModels();

function insertBreadcrumb(iframe, { content = "Breadcrumb Content" } = {}) {
    const wrapwrap = iframe.contentDocument.querySelector("#wrapwrap");
    const wrap = wrapwrap.querySelector("#wrap");
    const main = iframe.contentDocument.createElement("main");
    const breadcrumb = iframe.contentDocument.createElement("div");
    breadcrumb.className = "o_page_breadcrumb";
    breadcrumb.setAttribute("data-name", "Breadcrumb");
    breadcrumb.textContent = content;
    wrap.parentNode.insertBefore(main, wrap);
    main.appendChild(breadcrumb);
    return breadcrumb;
}

test("BreadcrumbVisibility option should appear without overTheContent", async () => {
    await setupWebsiteBuilder("", {
        beforeWrapwrapContent: `<input type="hidden" class="o_page_option_data" name="breadcrumb_visible">`,
        onIframeLoaded: (iframe) => insertBreadcrumb(iframe),
    });
    await contains(":iframe .o_page_breadcrumb").click();
    await waitFor("[data-label='Breadcrumb Position']");
    expect("[data-label='Breadcrumb Position']").toBeVisible();
    await contains("[data-label='Breadcrumb Position'] .dropdown").click();
    expect(".o-overlay-container [data-action-value='overTheContent']").not.toHaveCount();
});

test("BreadcrumbVisibility option should appear with overTheContent", async () => {
    await setupWebsiteBuilder("", {
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_overlay">`,
        onIframeLoaded: (iframe) => insertBreadcrumb(iframe),
    });
    await contains(":iframe .o_page_breadcrumb").click();
    await waitFor("[data-label='Breadcrumb Position']");
    expect("[data-label='Breadcrumb Position']").toBeVisible();
    await contains("[data-label='Breadcrumb Position'] .dropdown").click();
    expect(".o-overlay-container [data-action-value='overTheContent']").toBeVisible();
});

test("undo/redo Breadcrumb visibility options", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_overlay">`,
        onIframeLoaded: (iframe) => insertBreadcrumb(iframe),
    });
    const editor = getEditor();
    await contains(":iframe .o_page_breadcrumb").click();
    const precedentBreadcrumb = queryOne(":iframe .o_page_breadcrumb").outerHTML;
    await contains("[data-label='Breadcrumb Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='overTheContent']").click();
    undo(editor);
    redo(editor);
    undo(editor);
    const modifiedBreadcrumb = queryOne(":iframe .o_page_breadcrumb");
    expect(modifiedBreadcrumb).toHaveOuterHTML(precedentBreadcrumb);
    await contains("[data-label='Breadcrumb Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='hidden']").click();
    undo(editor);
    redo(editor);
    undo(editor);
    const newModifiedBreadcrumb = queryOne(":iframe .o_page_breadcrumb");
    expect(newModifiedBreadcrumb).toHaveOuterHTML(precedentBreadcrumb);
    // test the invisible elements panel
    await contains(":iframe .o_page_breadcrumb").click();
    await contains("[data-label='Breadcrumb Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='hidden']").click();
    expect(modifiedBreadcrumb).toHaveClass("d-none");
    await contains(".o_we_invisible_el_panel div:contains('Breadcrumb')").click();
    expect(modifiedBreadcrumb).not.toHaveClass("d-none");
});

test("Breadcrumb over the content displays background and text color options", async () => {
    const { getEditor } = await setupWebsiteBuilder("", {
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_overlay">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_color">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_text_color">`,
        onIframeLoaded: (iframe) => insertBreadcrumb(iframe),
    });
    const editor = getEditor();
    await contains(":iframe .o_page_breadcrumb").click();
    await waitFor("[data-label='Breadcrumb Position']");
    await contains("[data-label='Breadcrumb Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='overTheContent']").click();
    await waitFor("[data-label='Background']");
    await waitFor("[data-label='Text Color']");
    expect("[data-label='Background']").toBeVisible();
    expect("[data-label='Text Color']").toBeVisible();
    await contains("[data-label='Background'].hb-row-sublevel-1 .o_we_color_preview").click();
    await contains("[data-color='600']").click();
    const precedentBreadcrumb = queryOne(":iframe .o_page_breadcrumb").outerHTML;
    await contains("[data-label='Breadcrumb Position'] .dropdown").click();
    await contains(".o-overlay-container [data-action-value='regular']").click();
    undo(editor);
    redo(editor);
    undo(editor);
    const modifiedBreadcrumb = queryOne(":iframe .o_page_breadcrumb");
    expect(modifiedBreadcrumb).toHaveOuterHTML(precedentBreadcrumb);
});
