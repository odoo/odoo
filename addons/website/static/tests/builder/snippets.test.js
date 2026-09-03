import { getDragHelper } from "@html_builder/../tests/helpers";
import { expect, test, waitFor } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
    waitForSnippetDialog,
} from "./website_helpers";

defineWebsiteModels();

test("Can't drop some snippets in the s_table_of_content snippet", async () => {
    await setupWebsiteBuilderWithSnippet("s_table_of_content");
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    await moveTo(":iframe .s_table_of_content .oe_drop_zone:nth-child(3)");
    expect(":iframe .s_table_of_content .oe_drop_zone:nth-child(3)").toHaveClass(
        "o_dropzone_highlighted"
    );
    await drop(getDragHelper());
    await waitForSnippetDialog();
    const snippetsToTest = ["s_popup", "s_tabs", "s_table_of_content", "s_faq_horizontal"];
    for (const snippet of snippetsToTest) {
        await contains(".o_add_snippet_dialog_search").edit(snippet);
        expect(`.modal-dialog :iframe [data-snippet-id='${snippet}']`).toHaveCount(0);
    }
});

test("Can't drop some snippets in the s_tabs snippet", async () => {
    await setupWebsiteBuilderWithSnippet("s_tabs");
    const { moveTo, drop } = await contains(
        ".o-snippets-menu #snippet_groups .o_snippet_thumbnail"
    ).drag();
    await moveTo(":iframe .s_tabs_main .oe_drop_zone");
    await drop(getDragHelper());
    await waitForSnippetDialog();
    const snippetsToTest = ["s_popup", "s_tabs", "s_table_of_content"];
    for (const snippet of snippetsToTest) {
        await contains(".o_add_snippet_dialog_search").edit(snippet);
        expect(`.modal-dialog :iframe [data-snippet-id='${snippet}']`).toHaveCount(0);
    }
});

test("Disable undroppable snippets after custom snippet save", async () => {
    onRpc("ir.ui.view", "save_snippet", () => "Custom popup");
    await setupWebsiteBuilderWithSnippet("s_popup");

    const popupModal = await waitFor(":iframe .s_popup .modal");
    popupModal.classList.add("show");

    await contains(":iframe .s_popup").click();
    await contains(".oe_snippet_save").click();
    await contains(".o_technical_modal button:contains('Save')").click();

    await contains("#blocks-tab").click();
    await contains(".o_snippets_container .o_snippet_thumbnail button").click();
    await waitForSnippetDialog();

    await contains(".o_add_snippet_dialog_search").edit("s_popup");
    await waitFor(".o_add_snippet_dialog:contains('No snippets found.')");
});
