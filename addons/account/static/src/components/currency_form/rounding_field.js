import { registry } from "@web/core/registry";
import { useDebounced } from "@web/core/utils/timing";
import { FloatField, floatField } from "@web/views/fields/float/float_field";

export class CurrencyRoundingField extends FloatField {
    static template = "account.CurrencyRoundingField";

    setup() {
        super.setup();
        this.commitWhileTyping = useDebounced((value) => {
            if (value !== this.props.record.data[this.props.name]) {
                this.props.record.update({ [this.props.name]: value });
            }
        }, 300);
    }

    /**
     * Commit the value while typing, so that the warnings relying 
     * on display_rounding_warning show up before the user can save.
     */
    onInput(ev) {
        let value;
        try {
            value = this.parse(ev.target.value);
        } catch {
            return; // The user is still typing an incomplete value, e.g. "0."
        }
        this.commitWhileTyping(value);
    }
}

registry.category("fields").add("currency_rounding", {
    ...floatField,
    component: CurrencyRoundingField,
});
