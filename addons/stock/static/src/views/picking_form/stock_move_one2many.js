import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { many2OneField } from "@web/views/fields/many2one/many2one_field";
import {
    ProductNameAndDescriptionListRendererMixin,
    ProductNameAndDescriptionField
} from "@product/product_name_and_description/product_name_and_description";
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

export class MoveProductLabelField extends ProductNameAndDescriptionField {
    static template = "stock.MoveProductLabelField";

    setup() {
        super.setup();
        this.descriptionColumn = "description_picking";
    }

    get completeLabel() {
        return this.props.record.data[this.descriptionColumn];
    }

    get label() {
        const product = this.props.record.data;
        let label = product[this.descriptionColumn];
        if (label.startsWith(product.product_id[1])) {
            label = label.split(product.product_id[1])[1].trim();
        }
        return label;
    }

    get nonDraftTextareaVisible() {
        return (this.columnIsProductAndLabel.value && this.label) || (!this.columnIsProductAndLabel.value && !this.productName && this.label) || this.labelVisibility.value
    }

    updateLabel(value) {
        this.props.record.update({
          [this.descriptionColumn]: value,
        });
    }

    get doneOrCancelled() {
        return this.props.record.data.state === 'done' || this.props.record.data.state === 'cancel';
    }
}

export const moveProductLabelField = {
    ...many2OneField,
    component: MoveProductLabelField,
};
registry.category("fields").add("move_product_label_field", moveProductLabelField);
