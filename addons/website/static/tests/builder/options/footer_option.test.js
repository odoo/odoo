import { expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { contains, mockService, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("skip saving page options when the relevant element is not in the DOM", async () => {
    mockService("website", {
        get currentWebsite() {
            return {
                metadata: {
                    mainObject: {
                        model: "website.page",
                        id: 4,
                    },
                },
                default_lang_id: {
                    code: "en_US",
                },
            };
        },
    });
    await setupWebsiteBuilder("", {
        beforeWrapwrapContent: `
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_overlay">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_color">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_text_color">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="header_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="footer_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_visible">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_overlay">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_color">
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="breadcrumb_text_color">`,
        footerContent: `
            <footer data-name="Footer">Footer Content</footer>`,
    });
    onRpc("website.page", "write", ({ args }) => {
        expect(args[1]).toEqual({
            footer_visible: false,
        });
        return true;
    });
    await contains(":iframe #wrapwrap > footer").click();
    await contains("[data-label='Page Visibility'] input").click();
    await contains(".o-snippets-top-actions [data-action='save']").click();
});

test("footer content width is applied from the footer element", async () => {
    onRpc("/website/theme_customize_data_get", () => ["website.footer_content_width_fluid"]);
    onRpc("/website/theme_customize_data", async (request) => {
        const { params } = await request.json();
        expect.step(`theme_customize_data enable=${params.enable} disable=${params.disable}`);
    });
    onRpc("ir.ui.view", "save", () => {
        expect.step("save");
        return true;
    });
    await setupWebsiteBuilder("", {
        footerContent: `
            <footer id="bottom" class="o_footer o_footer_content_width_fluid">
                <div id="footer" class="oe_structure oe_structure_solo" data-oe-model="ir.ui.view" data-oe-id="5" data-oe-field="arch" data-oe-xpath="/data/xpath/div">
                    <section><div class="container">Content</div></section>
                </div>
            </footer>`,
    });
    await contains(":iframe #wrapwrap > footer").click();
    // Wait for the applied views to be loaded.
    await waitFor("[data-label='Content width'] [data-action-param*='content_width_fluid'].active");
    const smallButton = "[data-label='Content width'] [data-action-param*='content_width_small']";

    await contains(smallButton).hover();
    expect(":iframe #wrapwrap > footer").toHaveClass("o_footer_content_width_small");
    expect(":iframe #wrapwrap > footer").not.toHaveClass("o_footer_content_width_fluid");
    expect(":iframe #footer section > div").toHaveAttribute("class", "container");

    await contains(smallButton).click();
    // Only the views are toggled: the footer content is not modified, so it
    // is not saved.
    expect.verifySteps([
        "theme_customize_data enable=website.footer_content_width_small disable=website.footer_content_width_fluid",
    ]);
    expect(":iframe #footer section > div").toHaveAttribute("class", "container");
});
