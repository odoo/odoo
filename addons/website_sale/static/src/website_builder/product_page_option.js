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
        this.getZoomLevels = this.dependencies.productPageOption.getZoomLevels;
        this.domState = useDomState((el) => {
            const productDetailMainEl = el.querySelector("#product_detail_main");
            const productPageCarouselEl = el.querySelector("#o-carousel-product");
            const productPageGridEl = el.querySelector("#o-grid-product");
            const hasImages = productDetailMainEl.dataset.image_width !== "none";
            const isFullImage = productDetailMainEl.dataset.image_width === "100_pc";
            const multipleImages =
                hasImages &&
                productDetailMainEl.querySelector(".o_wsale_product_images").dataset.imageAmount >
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
