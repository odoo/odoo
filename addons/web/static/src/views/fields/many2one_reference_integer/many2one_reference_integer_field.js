import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { IntegerField } from "@web/views/fields/integer/integer_field";

export class Many2OneReferenceIntegerField extends IntegerField {
    get value() {
        const value = this.props.record.data[this.props.name];
        return value ? value.resId : false;
    }
}

const many2oneReferenceIntegerField = {
    component: Many2OneReferenceIntegerField,
    displayName: _t("Many2OneReferenceInteger"),
    supportedTypes: ["many2one_reference"],
};

registry.category("fields").add("many2one_reference_integer", many2oneReferenceIntegerField);
