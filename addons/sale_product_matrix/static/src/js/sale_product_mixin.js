import { useMatrixConfigurator } from "@product_matrix/js/matrix_configurator_hook";
import {
    SaleOrderLineProductField,
    saleOrderLineProductField,
} from "@sale/js/sale_product_field/sale_product_field";
import {
    listSaleOrderLineLabelText,
    SaleLabelTextField,
} from "@sale/js/sale_label_text/sale_label_text";
import { patch } from "@web/core/utils/patch";

const saleMatrixProductMixin = () => ({
    setup() {
        super.setup(...arguments);
        this.matrixConfigurator = useMatrixConfigurator();
    },

    async _openGridConfigurator(edit = false) {
        return this.matrixConfigurator.open(this.props.record, edit);
    },

    async _openProductConfigurator(edit = false, selectedComboItems = [], preloadedData) {
        if (edit && this.props.record.data.product_add_mode == "matrix") {
            this._openGridConfigurator(true);
        } else {
            return super._openProductConfigurator(...arguments);
        }
    },
});

patch(SaleLabelTextField.prototype, saleMatrixProductMixin());
patch(SaleOrderLineProductField.prototype, saleMatrixProductMixin());

Object.assign(saleOrderLineProductField, {
    fieldDependencies: [
        ...saleOrderLineProductField.fieldDependencies,
        { name: "product_add_mode", type: "selection" },
    ],
});

Object.assign(listSaleOrderLineLabelText, {
    fieldDependencies: [
        ...listSaleOrderLineLabelText.fieldDependencies,
        { name: "product_add_mode", type: "selection" },
    ],
});
