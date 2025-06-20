import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { ProductNameAndDescriptionListRendererMixin } from "@product/product_name_and_description/product_name_and_description";
import { patch } from "@web/core/utils/patch";

export class MovesListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.descriptionColumn = "description_picking";
        this.productColumns = ["product_id", "product_template_id"];
    }
}

patch(MovesListRenderer.prototype, ProductNameAndDescriptionListRendererMixin);

export class StockMoveX2ManyField extends X2ManyField {
    static components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };
}


export const stockMoveX2ManyField = {
    ...x2ManyField,
    component: StockMoveX2ManyField,
};

registry.category("fields").add("stock_move_one2many", stockMoveX2ManyField);
