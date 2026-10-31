import { registry } from "@web/core/registry";
import {
    BooleanToggleField,
    booleanToggleField,
} from "@web/views/fields/boolean_toggle/boolean_toggle_field";

export class TrustBankToggleField extends BooleanToggleField {
    async onChange(newValue) {
        await super.onChange(newValue);
        const { name, record } = this.props;
        if (record.isNew || record !== record.model.root) {
            return;
        }
        // Save right away, as trusting locks the fields: if it can't be saved, revert it to keep them editable.
        let saved = false;
        try {
            saved = await record.save();
        } finally {
            if (!saved) {
                await record.update({ [name]: !newValue });
            }
        }
    }
}

export const trustBankToggleField = {
    ...booleanToggleField,
    component: TrustBankToggleField,
};

registry.category("fields").add("trust_bank_toggle", trustBankToggleField);
