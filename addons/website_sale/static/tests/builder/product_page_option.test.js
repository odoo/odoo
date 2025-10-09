import { expect, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import { contains, dataURItoBlob, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Product page options", async () => {
    const { waitSidebarUpdated } = await setupWebsiteBuilder(`
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
                                    data-oe-xpath="/t[1]/div[2]/div[1]" data-oe-model="product.product" data-oe-id="14"
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
    onRpc("ir.ui.view", "save", () => {
        expect.step("save");
        return [];
    });

    const base64Image = (
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5"
        + "AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYIIA"
    );
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
            // converted image won't be used if original is not larger
            return dataURItoBlob(base64Image + "A".repeat(1000));
        },
        { pure: true },
    );
    onRpc("/html_editor/modify_image/1", () => {
        expect.step("modify_image");
        return base64Image; // Simulate image compression/convertion
    });

    await contains(":iframe .o_wsale_product_page").click();
    await contains("[data-action-id=productReplaceMainImage]").click();
    await contains(".o_select_media_dialog img").click();
    await expect.waitForSteps(["theme_customize_data_get", "get_image_info"]);
    await waitForNone(".o_select_media_dialog");

    expect(":iframe #product_detail_main img[src^='data:image/webp;base64,']").toHaveCount(1);
    expect(":iframe img").toHaveCount(2);
    // Avoid selecting the first option to prevent the image layout option from disappearing
    await contains("[data-action-id=productPageImageWidth][data-action-value='50_pc']").click();

    await waitSidebarUpdated();
    await expect.waitForSteps(["config", "modify_image", "save", "theme_customize_data_get"]);

    await contains("button#o_wsale_image_layout").click();
    await contains("[data-action-id=productPageImageLayout]").click();
    await waitSidebarUpdated();
    await expect.waitForSteps(["theme_customize_data", "config", "theme_customize_data_get"]);
 
    // Make sure that clicking quickly on a builder button after an clicking on
    // an action that reloads the editor does not produce a crash.
    await contains("[data-action-id=productPageImageWidth][data-action-value='66_pc']").click();
    await contains("button#o_wsale_image_layout").click();
    await expect.waitForSteps(["config", "theme_customize_data_get"]);
});
