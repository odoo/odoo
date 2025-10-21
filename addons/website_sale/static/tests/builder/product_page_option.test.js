import { expect, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import {
    contains,
    dataURItoBlob,
    defineModels,
    models,
    onRpc,
} from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

class ProductRibbon extends models.Model {
    _name = "product.ribbon";
}

defineWebsiteModels();
defineModels([ProductRibbon]);

test("Product page options", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
        <main>
            <div class="o_wsale_product_page">
                <section
                    id="product_detail"
                    class="oe_website_sale mt-1 mt-lg-2 mb-5 o_wsale_container_lg container-lg
                        o_wsale_product_page_opt_image_width_66_pc
                        o_wsale_product_page_opt_image_ratio_1_1
                        o_wsale_product_page_opt_image_ratio_mobile_auto
                        o_wsale_product_page_opt_image_radius_none
                        o_wsale_product_page_opt_separators"
                >
                    <div id="product_detail_main" data-image_layout="carousel">
                        <div class="o_wsale_product_images" data-image-amount="2">
                            <div id="o-carousel-product">
                                <div class="carousel-item h-100 text-center active o_colored_level" style="min-height: 693px;">
                                    <div name="o_img_with_max_suggested_width"
                                        class="d-flex align-items-start justify-content-center h-100 oe_unmovable o_editable"
                                        data-oe-xpath="/t[1]/div[2]/div[1]" data-oe-model="product.product" data-oe-id="13"
                                        data-oe-field="image_1920" data-oe-type="image"
                                        data-oe-expression="product_image.image_1920" contenteditable="false">
                                        <img>
                                    </div>
                                </div>
                                <div class="carousel-item h-100 text-center active o_colored_level" style="min-height: 693px;">
                                    <div name="o_img_with_max_suggested_width"
                                        class="d-flex align-items-start justify-content-center h-100 oe_unmovable o_editable"
                                        data-oe-xpath="/t[1]/div[2]/div[1]" data-oe-model="product.product" data-oe-id="14"
                                        data-oe-field="image_1920" data-oe-type="image"
                                        data-oe-expression="product_image.image_1920" contenteditable="false">
                                        <img>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </main>`);

    onRpc("/website/theme_customize_data", () => expect.step("theme_customize_data"));
    onRpc("/website/theme_customize_data_get", () => expect.step("theme_customize_data_get"));
    onRpc("/shop/config/website", () => expect.step("config"));
    onRpc("ir.ui.view", "save", () => {
        expect.step("save");
        return [];
    });

    const base64Image =
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5" +
        "AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYIIA";
    onRpc("ir.attachment", "search_read", () => [
        {
            mimetype: "image/png",
            image_src: "/web/image/hoot.png",
            access_token: false,
            public: true,
        },
    ]);
    onRpc("/html_editor/get_image_info", () => {
        expect.step("get_image_info");
        return {
            attachment: { id: 1 },
            original: { id: 1, image_src: "/web/image/hoot.png", mimetype: "image/png" },
        };
    });
    onRpc("/web/image/hoot.png", () => {
        // converted image won't be used if original is not larger
        return dataURItoBlob(base64Image + "A".repeat(1000));
    });
    onRpc("/html_editor/modify_image/1", () => {
        expect.step("modify_image");
        return base64Image; // Simulate image compression/convertion
    });

    await contains(":iframe .o_wsale_product_page").click();
    await contains("[data-action-id=productReplaceMainImage]").click();
    await contains(".o_select_media_dialog .o_existing_attachment_cell button").click();
    await expect.waitForSteps(["theme_customize_data_get", "get_image_info"]);
    await waitForNone(".o_select_media_dialog");

    expect(":iframe #product_detail_main img[src^='data:image/webp;base64,']").toHaveCount(1);
    expect(":iframe img").toHaveCount(2);
    await contains("button#o_wsale_image_width").click();
    // Avoid selecting the first option to prevent the image layout option from disappearing
    await contains("[data-action-id=productPageImageWidth][data-action-value='50_pc']").click();
    await waitSidebarUpdated();
    await expect.waitForSteps(["config"]);

    await contains("button#o_wsale_image_layout").click();
    await contains("[data-action-id=productPageImageLayout]").click();
    await waitSidebarUpdated();
    await expect.waitForSteps([
        // Activate the carousel view and change the shop config
        "config",
        // Shop config changes don't trigger the `savePlugin`; image edits are saved because of the
        // theme customization.
        "modify_image",
        // Save the pending image width class changes
        "save",
        // Save the image changes
        "save",
        // Reload the view
        "theme_customize_data_get",
    ]);

    // Make sure that clicking quickly on a builder button after an clicking on
    // an action that reloads the editor does not produce a crash.
    await contains("[data-action-id=websiteConfig].o_we_buy_now_btn").click();
    await contains("button#o_wsale_image_layout").click();
    await expect.waitForSteps(["theme_customize_data", "theme_customize_data_get"]);
});
