import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { unaccent } from "@web/core/utils/strings";

patch(ProductScreen.prototype, {
    getProductsBySearchWord(searchWord) {
        const words = unaccent(searchWord.toLowerCase(), false);
        const products = this.pos.selectedCategory?.id
            ? this.getProductsByCategory(this.pos.selectedCategory)
            : this.products;

        const exactMatches = products.filter((product) => product.exactMatch(words));

        if (exactMatches.length > 0 && words.length > 2) {
            return exactMatches;
        }

        const matches = products.filter((p) => {
            if (p.alternative_name) {
                const altNameMatch = unaccent(p.alternative_name, false)
                    .toLowerCase()
                    .includes(words);
                return altNameMatch;
            }
            const searchStringMatch = unaccent(p.searchString, false).toLowerCase().includes(words);
            return searchStringMatch;
        });

        return Array.from(new Set([...exactMatches, ...matches]));
    },
});
