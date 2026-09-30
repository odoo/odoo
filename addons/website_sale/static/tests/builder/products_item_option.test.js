import { expect, test } from "@odoo/hoot";
import { contains, defineModels, models, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

class productRibbon extends models.Model {
    _name = "product.ribbon";
}

defineWebsiteModels();
defineModels([productRibbon]);

test("add a new ribbon", async () => {
    onRpc("product.ribbon", "create", () => [1]);
    onRpc("product.template", "write", () => ({}));
    await setupWebsiteBuilder(
        `<div id="o_wsale_container" data-ppg="20" data-ppr="4" data-default-sort="website_sequence asc">
        <div id="products_grid">
            <section id="o_wsale_products_grid" class="o_wsale_products_grid_table grid o_wsale_products_grid_table_md" style="--o-wsale-ppr: 4; --o-wsale-ppg: 20" data-name="Grid">
                <div class="oe_product" style="--o-wsale-products-grid-product-col-height: 1;" data-name="Product">
                <div class="o_wsale_product_grid_wrapper o_wsale_product_grid_wrapper_1_1">
                <form class="oe_product_cart" data-publish="off">
                    <div class="oe_product_image">
                        <a class="oe_product_image_link d-block position-relative" contenteditable="false" href="/shop/event-registration-4">
                            <span class="oe_product_image_img_wrapper d-flex h-100 justify-content-center align-items-center position-absolute"><img src="/web/image/product.template/4/image_512/product?unique=5c2586b" class="img img-fluid h-100 w-100 position-absolute"></span>
                            <span class="o_ribbon o_not_editable d-none" style=""></span>
                        </a>
                    </div>
                    <span
                        data-ribbon-id=""
                        class="o_ribbons o_not_editable"
                        style=""
                    />
                    <div class="o_wsale_product_information">
                            <div class="o_wsale_product_information_text">
                                <h6 class="o_wsale_products_item_title">
                                    <a data-oe-model="product.template" data-oe-id="4" data-oe-field="name" data-oe-type="char" data-oe-expression="product.name">
                                        Test product
                                    </a>
                                </h6>
                            </div>
                        <div class="o_wsale_product_sub">
                            <div class="product_price">
                                <span class="oe_currency_value">1.00</span>
                            </div>
                        </div>
                    </div>
                </form>
                </div>
                </div>
            </section>
        </div>
        </div>`
    );
    await contains(":iframe .oe_product").click();
    await contains("button[data-action-id='createRibbon']").click();
    expect(":iframe .oe_product .o_ribbons").toHaveText("Ribbon Name");
});
