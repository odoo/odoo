import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Using the 'Content Width' option should display a container preview", async () => {
    await setupWebsiteBuilderWithSnippet("s_banner", { loadIframeBundles: true });
    await contains(":iframe .s_banner").click();
    await contains("[data-label='Content Width'] button").hover();
    expect(":iframe .o_container_small.o_container_preview").toHaveCount(1);
    await contains("[data-label='Content Width'] button").click();
    expect(":iframe .o_container_small").not.toHaveClass("o_container_preview");
});
