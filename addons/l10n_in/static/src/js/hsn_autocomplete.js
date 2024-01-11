/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class HsnAutoComplete extends Component {
    static template = "hsn_autocomplete.HsnAutoComplete";
    static components = { AutoComplete };
    setup() {
        this.orm = useService("orm");
    }

    async validateSearchTerm(request) {
        return request && request.length > 2;
    }

    get sources() {
        return [
            {
                options: async (request) => {
                    if (await this.validateSearchTerm(request)) {
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
        if (this.props.hsn_description_field) {
            this.props.record.update({
                [this.props.name]: option.c,
                [this.props.hsn_description_field]: option.n,
            });
        } else {
            this.props.record.update({ [this.props.name]: option.c });
        }
    }
}

export const hsnAutoComplete = {
    component: HsnAutoComplete,
    supportedOptions: [
        {
            label: _t("Hsn description field"),
            name: "hsn_description_field",
            type: "string",
        },
    ],
    supportedTypes: ["char"],
    extractProps: ({ options }) => ({
        hsn_description_field: options.hsn_description_field,
    }),
};

registry.category("fields").add("hsn_autocomplete", hsnAutoComplete);
