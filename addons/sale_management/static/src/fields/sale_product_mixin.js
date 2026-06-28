import { SaleOrderLineProductField } from "@sale/js/sale_product_field/sale_product_field";
import { SaleLabelTextField } from "@sale/js/sale_label_text/sale_label_text";
import { patch } from "@web/core/utils/patch";

const saleManagementProductMixin = () => ({
    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();

        const isOptionalLine = this.env.shouldCollapse(this.props.record, "is_optional");
        props.options = {
            showQuantity: !isOptionalLine,
            showPrice: !isOptionalLine,
        };

        return props;
    },

    _prepareNewLineData(line, product) {
        const data = super._prepareNewLineData(line, product);
        if (this.env.shouldCollapse(line, "is_optional")) {
            data.quantity = 0;
        }
        return data;
    },
});

patch(SaleLabelTextField.prototype, saleManagementProductMixin());
patch(SaleOrderLineProductField.prototype, saleManagementProductMixin());
