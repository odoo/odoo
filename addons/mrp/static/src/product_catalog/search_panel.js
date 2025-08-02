import { ProductCatalogSearchPanel } from "@product/product_catalog/search/search_panel";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogSearchPanel.prototype, {
    get showSections() {
        return (
            super.showSections
            && this.env.model.config.context.product_catalog_order_model !== 'mrp.production'
        );
    }
});
