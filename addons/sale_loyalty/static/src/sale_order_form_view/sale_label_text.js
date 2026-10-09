import { SaleLabelTextField } from "@sale/js/sale_label_text/sale_label_text";
import { patch } from "@web/core/utils/patch";

patch(SaleLabelTextField.prototype, {
    get canEditProduct() {
        // The label of a reward line starts with its description, not with its product
        return super.canEditProduct && !this.props.record.data.is_reward_line;
    },
});
