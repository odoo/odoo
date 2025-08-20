import { expect, test } from "@odoo/hoot";
import { waitForNone } from "@odoo/hoot-dom";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Replace Main Image", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    await setupWebsiteBuilder(`
        <main>
            <div class="o_wsale_product_page">
                <div id="product_detail_main">
                    <div class="o_wsale_product_images">
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
                        </div>
                    </div>
                </div>
            </div>
        </main>`);

    await contains(":iframe .o_wsale_product_page").click();
    await contains("[data-action-id=productReplaceMainImage]").click();
    await contains(".o_select_media_dialog img").click();
    await waitForNone(".o_select_media_dialog");

    expect(":iframe #product_detail_main img[src^='data:image/webp;base64,']").toHaveCount(1);
    expect(":iframe img").toHaveCount(1);
});
