import { registry } from "@web/core/registry";
import { booleanToggleField, BooleanToggleField } from "./boolean_toggle_field";

export class ListBooleanToggleField extends BooleanToggleField {
    static template = "web.ListBooleanToggleField";

    async onClick() {
        if (!this.props.readonly && this.props.record.isInEdition) {
            const changes = { [this.props.name]: !this.props.record.data[this.props.name] };
            await this.props.record.update(changes, { save: this.props.autosave });
        }
    }
}

export const listBooleanToggleField = {
    ...booleanToggleField,
    component: ListBooleanToggleField,
};

registry.category("fields").add("list.boolean_toggle", listBooleanToggleField);
