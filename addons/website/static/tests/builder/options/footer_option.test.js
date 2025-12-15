import { expect, test } from "@odoo/hoot";
import { contains, mockService, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("saving page after footer visibility change should work when header is not present", async () => {
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
            <input type="hidden" class="o_page_option_data" autocomplete="off" name="footer_visible">`,
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
