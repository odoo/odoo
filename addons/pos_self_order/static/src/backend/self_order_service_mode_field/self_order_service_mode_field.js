import { registry } from "@web/core/registry";
import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";

// Hides "Dynamic QR" when the config is a kiosk, since it only applies to mobile self ordering
export class SelfOrderServiceModeField extends SelectionField {
    get options() {
        const options = super.options;
        if (this.props.record.data.pos_self_ordering_mode === "kiosk") {
            return options.filter(([value]) => value !== "dynamic_qr");
        }
        return options;
    }
}

export const selfOrderServiceModeField = {
    ...selectionField,
    component: SelfOrderServiceModeField,
};

registry.category("fields").add("self_order_service_mode_selection", selfOrderServiceModeField);
