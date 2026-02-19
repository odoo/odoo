import { patch } from "@web/core/utils/patch";
import { SMLX2ManyField } from "@stock/fields/stock_move_line_x2_many_field";

patch(SMLX2ManyField.prototype, {
    async onAdd({ context, editable }) {
        const { show_quant, use_expiration_date } = this.props.record.data;
        if (show_quant) {
            context = { ...context, use_expiration_date };
        }
        return super.onAdd({ context, editable });
    }
});
