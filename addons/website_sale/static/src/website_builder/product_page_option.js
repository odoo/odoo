import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { _t } from "@web/core/l10n/translation";

export class ProductPageOption extends BaseOptionComponent {
    static template = "website_sale.ProductPageOption";
    static dependencies = ["productPageOption"];
    static selector = "main:has(.o_wsale_product_page)";
    static title = _t("Product Page");
    static editableOnly = false;

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
