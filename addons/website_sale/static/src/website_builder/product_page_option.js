import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export const PRODUCT_PAGE_OPTION_SELECTOR = "main:has(.o_wsale_product_page)";

export class ProductPageOption extends BaseOptionComponent {
    static id = "product_page_option";
    static template = "website_sale.ProductPageOption";
    static dependencies = ["productPageOption"];

    setup() {
        super.setup();
        this.domState = useDomState((el) => {
            const productDetailEl = el.querySelector("#product_detail");
            const productDetailMainEl = el.querySelector("#product_detail_main");
            const productPageCarouselEl = el.querySelector("#o-carousel-product");
            const productPageGridEl = el.querySelector("#o-grid-product");
            const hasImages = !productDetailEl.classList.contains(
                "o_wsale_product_page_opt_image_width_none"
            );
            const isFullImage = productDetailEl.classList.contains(
                "o_wsale_product_page_opt_image_width_100_pc"
            );
            const multipleImages =
                hasImages &&
                productDetailMainEl.querySelector(".o_wsale_product_images")?.dataset.imageAmount >
                    1;
            const isGrid = !!productDetailMainEl.querySelector("#o-grid-product");
            const hasCarousel = !!productPageCarouselEl;
            const hasGrid = !!productPageGridEl;
            return {
                hasImages,
                isFullImage,
                multipleImages,
                isGrid,
                hasCarousel,
                hasGrid,
            };
        });
    }
}

registry.category("website-options").add(ProductPageOption.id, ProductPageOption);
