import { AccountProductCatalogSearchPanel } from "@account/components/product_catalog/search/search_panel/search_panel";
import { patch } from "@web/core/utils/patch";

patch(AccountProductCatalogSearchPanel.prototype, {
    get showSectionAmounts() {
        return super.showSectionAmounts && this.orderModel !== "sale.order.template";
    },
});
