import { useMatrixConfigurator } from "@product_matrix/js/matrix_configurator_hook";
import { SaleOrderLineProductField, saleOrderLineProductField } from "@sale/js/sale_product_field";
import { patch } from "@web/core/utils/patch";

patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup(...arguments);
        this.matrixConfigurator = useMatrixConfigurator();
    },

    async _openGridConfigurator(edit=false) {
        return this.matrixConfigurator.open(this.props.record, edit);
    },

    async _openProductConfigurator(edit=false, selectedComboItems=[]) {
        if (edit && this.props.record.data.product_add_mode == 'matrix') {
            this._openGridConfigurator(true);
        } else {
            return super._openProductConfigurator(...arguments);
        }
    },
});

Object.assign(saleOrderLineProductField, {
    fieldDependencies: [
        ...saleOrderLineProductField.fieldDependencies,
        { name: "product_add_mode", type: "selection"},
    ],
});
