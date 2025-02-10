import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { BooleanField, booleanField } from "@web/views/fields/boolean/boolean_field";

export class BooleanFieldLabeled extends BooleanField {
    static template = "hr_holidays.BooleanFieldLabeled";
    static props = {
        ...BooleanField.props,
        true_label: { type: String },
        false_label: { type: String },
    };
    setup() {
        super.setup(...arguments);
        useRecordObserver((record) => {
            this.state.label = record.data[this.props.name]
                ? this.props.true_label
                : this.props.false_label;
        });
    }
    async onChange(newValue) {
        super.onChange(...arguments);
        this.state.label = newValue ? this.props.true_label : this.props.false_label;
    }
}

export const booleanFieldLabeled = {
    ...booleanField,
    component: BooleanFieldLabeled,
    displayName: _t("BooleanLabeled"),
    supportedOptions: [
        {
            label: _t("Label"),
            name: "true_label",
            type: "string",
            help: _t("A clickable label for the toggle. Contains text for the true state."),
        },
        {
            label: _t("Label"),
            name: "false_label",
            type: "string",
            help: _t("A clickable label for the toggle. Contains text for the false state."),
        },
    ],
    extractProps({ options }, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
            true_label: options.true_label,
            false_label: options.false_label,
        };
    },
};

registry.category("fields").add("boolean_labeled", booleanFieldLabeled);
