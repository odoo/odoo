import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { unaccent } from "@web/core/utils/strings";

patch(ProductScreen.prototype, {
    getProductsBySearchWord(searchWord) {
        const words = unaccent(searchWord.toLowerCase(), false);
        const products = this.pos.selectedCategory?.id
            ? this.getProductsByCategory(this.pos.selectedCategory)
            : this.products;
        return products.filter((p) =>
            unaccent(p.alternative_name || p.searchString, false)
                .toLowerCase()
                .includes(words)
        );
    },

    get productsToDisplay() {
        return super.productsToDisplay.sort((a, b) =>
            (a.alternative_name || a.display_name).localeCompare(
                b.alternative_name || b.display_name
            )
        );
    },
});
