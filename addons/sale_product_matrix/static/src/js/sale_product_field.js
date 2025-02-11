import { useMatrixConfigurator } from "@product_matrix/js/matrix_configurator_hook";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field";
import { patch } from "@web/core/utils/patch";

patch(SaleOrderLineProductField.prototype, {
    setup() {
        super.setup();
        this.matrixConfigurator = useMatrixConfigurator();
    },
    openProductConfigurator(edit) {
        if (edit && this.props.record.data.product_add_mode === "matrix") {
            return this._openGridConfigurator(true);
        } else {
            return super.openProductConfigurator(edit);
        }
    },
    _openGridConfigurator(edit = false) {
        return this.matrixConfigurator.open(this.props.record, edit);
    },
});
