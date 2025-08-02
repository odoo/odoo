import { patch } from "@web/core/utils/patch";
import { DatetimePlaceholderField } from "@sale/js/datetime_placeholder_field/datetime_placeholder_field";

patch(DatetimePlaceholderField.prototype, {
    get placeholder() {
        const { delivery_status, effective_date } = this.props.record.data;
        return delivery_status === "full" && effective_date
            ? effective_date.toFormat("MM/dd/yyyy HH:mm")
            : super.placeholder;
    }
});
