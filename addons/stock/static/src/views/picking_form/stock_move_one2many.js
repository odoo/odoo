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
    static recordRowTemplate = "stock.MovesListRenderer.RecordRow";

    setup() {
        super.setup();
        this.descriptionColumn = "description_picking";
        this.productColumns = ["product_id", "product_template_id"];
    }

    processAllColumn(allColumns, list) {
        let cols = super.processAllColumn(...arguments);
        if (list.resModel === "stock.move") {
            cols.push({
                type: 'opendetailsop',
                id: `column_detailOp_${cols.length}`,
                column_invisible: 'parent.state=="draft"',
            });
        }
        return cols;
    }
}

patch(MovesListRenderer.prototype, ProductNameAndDescriptionListRendererMixin);

export class StockMoveX2ManyField extends X2ManyField {
    static components = { ...X2ManyField.components, ListRenderer: MovesListRenderer };
    setup() {
        super.setup();
        this.canOpenRecord = true;
    }

    get isMany2Many() {
        return false;
    }

    async openRecord(record) {
        if (this.canOpenRecord && !record.isNew) {
            const dirty = await record.isDirty();
            if (await record._parentRecord.isDirty() || (dirty && 'quantity' in record._changes)) {
                await record._parentRecord.save({ reload: true });
                record = record._parentRecord.data[this.props.name].records.find(e => e.resId === record.resId);
                if (!record) {
                    return;
                }
            }
        }
        return super.openRecord(record);
    }
}


export const stockMoveX2ManyField = {
    ...x2ManyField,
    component: StockMoveX2ManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
};

registry.category("fields").add("stock_move_one2many", stockMoveX2ManyField);

export class MoveProductLabelField extends ProductNameAndDescriptionField {
    static template = "stock.MoveProductLabelField";

    setup() {
        super.setup();
        this.descriptionColumn = "description_picking";
    }

    get productName() {
        return this.props.record.data[this.props.name][1];
    }

    get label() {
        return this.props.record.data[this.descriptionColumn];
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
registry
    .category("fields")
    .add("move_product_label_field", moveProductLabelField);
