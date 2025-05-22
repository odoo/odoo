import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class ProductPageOption extends BaseOptionComponent {
    static template = "website_sale.ProductPageOption";
    static props = {
        getZoomLevels: Function,
    };
    setup() {
        super.setup();
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
