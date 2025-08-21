import { expect, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import { contains, dataURItoBlob, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    waitForEndOfOperation,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Product page options", async () => {
    await setupWebsiteBuilder(`
        <main>
            <div class="o_wsale_product_page">
                <div id="product_detail_main" data-image_width="66_pc" data-image_layout="carousel">
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
                                    data-oe-xpath="/t[1]/div[2]/div[1]" data-oe-model="product.product" data-oe-id="13"
                                    data-oe-field="image_1920" data-oe-type="image"
                                    data-oe-expression="product_image.image_1920" contenteditable="false">
                                    <img>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>`);

    onRpc("/website/theme_customize_data", () => expect.step("theme_customize_data"));
    onRpc("/website/theme_customize_data_get", () => expect.step("theme_customize_data_get"));
    onRpc("/shop/config/website", () => expect.step("config"));
    onRpc("/html_editor/modify_image/1", () => expect.step("modify_image"));
    onRpc("ir.ui.view", "save", () => {
        expect.step("save");
        return [];
    });

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

    onRpc(
        "/web/image/hoot.png",
        () => {
            const base64Image =
                "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYIIA" +
                "A".repeat(1000); // converted image won't be used if original is not larger
            return dataURItoBlob(base64Image);
        },
        { pure: true },
    );

    await contains(":iframe .o_wsale_product_page").click();
    await contains("[data-action-id=productReplaceMainImage]").click();
    await contains(".o_select_media_dialog img").click();
    await waitForNone(".o_select_media_dialog");

    expect(":iframe #product_detail_main img[src^='data:image/webp;base64,']").toHaveCount(1);
    expect(":iframe img").toHaveCount(2);
    expect.verifySteps(["theme_customize_data_get", "get_image_info"]);

    await contains("[data-action-id=productPageImageWidth]").click();
    await waitForEndOfOperation();
    expect.verifySteps(["config", "modify_image", "save", "theme_customize_data_get"]);

    await contains("button#o_wsale_image_layout").click();
    await contains("[data-action-id=productPageImageLayout]").click();
    await waitForEndOfOperation();
    expect.verifySteps(["theme_customize_data", "config", "theme_customize_data_get"]);
});
