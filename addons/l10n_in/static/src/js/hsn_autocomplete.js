/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useService } from "@web/core/utils/hooks";

export class L10nInHsnAutoComplete extends CharField {
    static template = "hsn_autocomplete.L10nInHsnAutoComplete";
    static components = {
        ...CharField.components,
        AutoComplete,
    };
    static props = {
        ...CharField.props,
        l10n_in_hsn_description: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    get sources() {
        return [
            {
                options: async (request) => {
                    if (request?.length > 2) {
                        return await this.orm.call("product.template", "get_hsn_suggestions", [
                            request,
                        ]);
                    } else {
                        return [];
                    }
                },
                optionTemplate: "hsn_autocomplete.DropdownOption",
                placeholder: _t("Searching..."),
            },
        ];
    }

    onSelect(option) {
        const data = { [this.props.name]: option.c };
        if (this.props.l10n_in_hsn_description) {
            data[this.props.l10n_in_hsn_description] = option.n;
        }
        this.props.record.update(data);
    }
}

export const l10nInHsnAutoComplete = {
    ...charField,
    component: L10nInHsnAutoComplete,
    supportedOptions: [
        {
            label: _t("l10n_in hsn description"),
            name: "l10n_in_hsn_description",
            type: "string",
        },
    ],
    extractProps: ({ options }) => ({
        l10n_in_hsn_description: options.l10n_in_hsn_description,
    }),
};

registry.category("fields").add("l10n_in_hsn_autocomplete", l10nInHsnAutoComplete);
