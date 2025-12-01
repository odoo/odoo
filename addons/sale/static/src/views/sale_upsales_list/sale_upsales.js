import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ProductNameAndDescriptionListRendererMixin } from "@product/product_name_and_description/product_name_and_description";
import { patch } from "@web/core/utils/patch";

export class SaleOrderLineUpsells extends ListRenderer {

    setup() {
        super.setup();
        this.descriptionColumn = "name";
        this.productColumns = ["product_id", "product_template_id"];
    }
    
    getActiveColumns() {
        let activeColumns = super.getActiveColumns();
        let productTmplCol = activeColumns.find((col) => col.name === 'product_template_id');
        let productCol = activeColumns.find((col) => col.name === 'product_id');
        
        if (productCol && productTmplCol) {
            // Hide the template column if the variant one is enabled.
            activeColumns = activeColumns.filter((col) => col.name != 'product_template_id')
        }
        
        return activeColumns;
    }
}

patch(SaleOrderLineUpsells.prototype, ProductNameAndDescriptionListRendererMixin);

export const upsaleOrderLineListView = {
    ...listView,
    Renderer: SaleOrderLineUpsells,
};

registry.category("views").add("upsale_order_line_list", upsaleOrderLineListView);
