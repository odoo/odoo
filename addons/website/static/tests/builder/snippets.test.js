import { getDragHelper } from "@html_builder/../tests/helpers";
import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
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
    await moveTo(":iframe .s_table_of_content .oe_drop_zone");
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
