import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useChildRef } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";

const l10N_IN_HSN_SERVICE_URL = "https://services.gst.gov.in/commonservices/hsn/search/qsearch";

export class L10nInHsnAutoComplete extends CharField {
    static template = "l10n_in.hsnAutoComplete";
    static components = {
        ...CharField.components,
        AutoComplete,
    };
    static props = {
        ...CharField.props,
        l10nInHsnDescription: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.inputRef = useChildRef();
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            parse: (v) => this.parse(v),
            ref: this.inputRef,
        });
    }

    async getHsnSuggestions(value) {
        const suggestions = [];
        const onlyDigits = !isNaN(value) && value.indexOf(" ") < 0;
        const params = [
            { type: "byCode", category: "null" }, // For code
            { type: "byDesc", category: "P" }, // For products
            { type: "byDesc", category: "S" }, // For services
        ];
        const filteredParams = onlyDigits ? [params[0]] : params.slice(1);
        try {
            await Promise.all(
                filteredParams.map(async (param) => {
                    const controller = new AbortController();
                    const signal = controller.signal;
                    setTimeout(() => controller.abort(), 5000);
                    const res = await fetch(
                        `${l10N_IN_HSN_SERVICE_URL}?inputText=${value}&selectedType=${param.type}&category=${param.category}`,
                        { signal }
                    );
                    if (!res.ok) {
                        throw new Error(res.statusText);
                    }
                    const resData = await res.json();
                    for (const item of resData.data || []) {
                        if (item.c.length > 3) {
                            suggestions.push({
                                data: {
                                    description: item.n,
                                },
                                label: item.c,
                                onSelect: () => this.selectSuggestion(item.c, item.n),
                            });
                        }
                    }
                })
            );
        } catch (e) {
            suggestions.push({
                label: _t("Could not contact API"),
            });
            console.warn("HSN Autocomplete API error:", e);
        }
        return suggestions;
    }

    get sources() {
        return [
            {
                options: async (request) => {
                    if (request?.length > 2) {
                        return await this.getHsnSuggestions(request);
                    } else {
                        return [];
                    }
                },
                optionSlot: "option",
                placeholder: _t("Searching..."),
            },
        ];
    }

    selectSuggestion(label, description) {
        const data = { [this.props.name]: label };
        if (this.props.l10nInHsnDescription) {
            data[this.props.l10nInHsnDescription] = description;
        }
        setTimeout(() => this.props.record.update(data));
    }
}

export const l10nInHsnAutoComplete = {
    ...charField,
    component: L10nInHsnAutoComplete,
    supportedOptions: [
        {
            label: _t("hsn description field"),
            name: "hsn_description_field",
            type: "string",
        },
    ],
    extractProps: ({ options }) => ({
        l10nInHsnDescription: options.hsn_description_field,
    }),
};

registry.category("fields").add("l10n_in_hsn_autocomplete", l10nInHsnAutoComplete);
