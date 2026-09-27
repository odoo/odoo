import { expect, test } from "@odoo/hoot";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";
import { contains } from "@web/../tests/web_test_helpers";
import { queryOne } from "@odoo/hoot-dom";

defineWebsiteModels();

test("snippet vertical alignment", async () => {
    const snippets = ["s_key_images", "s_cards_soft", "s_cards_grid"];
    await setupWebsiteBuilderWithSnippet(["s_cards_soft", "s_key_images", "s_cards_grid"]);
    for (const snippet of snippets) {
        await contains(`:iframe .${snippet}`).click();
        const snippetRow = queryOne(`:iframe .${snippet} .row`);
        await contains("[data-action-param='align-items-start']").click();
        expect(snippetRow).toHaveClass("align-items-start");
        await contains("[data-action-param='align-items-center']").click();
        expect(snippetRow).toHaveClass("align-items-center");
        await contains("[data-action-param='align-items-end']").click();
        expect(snippetRow).toHaveClass("align-items-end");
        await contains("[data-action-param='align-items-stretch']").click();
        expect(snippetRow).toHaveClass("align-items-stretch");
    }
});
