import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RadioField, radioField } from "@web/views/fields/radio/radio_field";


class CustomRadioField extends RadioField {
    static props = {
        ...RadioField.props,
        hiddenItems: { type: Array, optional: true },
    };


    get items() {
        switch (this.type) {
            case "selection": {
                if (!this.props.hiddenItems) {
                    return this.props.record.fields[this.props.name].selection;
                }
                return this.props.record.fields[this.props.name].selection.filter((item) => !this.props.hiddenItems.includes(item[0]));
            }
            case "many2one": {
                return this.specialData.data;
            }
            default:
                return [];
        }
    }

}

export const customRadioField = {
    ...radioField,
    component: CustomRadioField,
    supportedOptions: [
        {
            label: _t("Display horizontally"),
            name: "horizontal",
            type: "boolean",
        },
        {
            label: _t("Hidden items"),
            name: "hiddenItems",
            type: "array",
        },
    ],
    extractProps: ({ options, string }, dynamicInfo) => ({
        orientation: options.horizontal ? "horizontal" : "vertical",
        hiddenItems: options.hiddenItems,
        label: string,
        domain: dynamicInfo.domain,
    }),
};

registry.category("fields").add("customRadio", customRadioField);
