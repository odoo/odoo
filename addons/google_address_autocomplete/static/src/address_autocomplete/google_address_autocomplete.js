import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { googlePlacesSession } from "../google_places_session";
import { useChildRef } from "@web/core/utils/hooks";
import { useInputField } from "@web/views/fields/input_field_hook";

const standardAddressFields = {
    street: {
        label: _t("Street field"),
        type: ["char"]
    },
    street2: {
        label: _t("Additional street field"),
        type: ["char"]
    },
    city: {
        label: _t("City field"),
        type: ["char"]
    },
    state_id: {
        label: _t("State field"),
        type: ["char", "many2one"]
    },
    zip: {
        label: _t("Zip field"),
        type: ["char"]
    },
    country_id: {
        label: _t("Country field"),
        type: ["char", "many2one"]
    }
}

export class AddressAutoComplete extends CharField {
    static template = "google_address_autocomplete.AddressAutoCompleteTemplate";
    static components = { AutoComplete, ...CharField.components };

    static props = {...CharField.props,
        addressFieldMap: {
            type: Object,
            optional: true,
        }
    }

    static defaultProps = {
        ...CharField.defaultProps,
        addressFieldMap: {},
    }

    setup() {
        super.setup();
        this.input = useChildRef();
        useInputField({
            ref: this.input,
            getValue: () => this.props.record.data[this.props.name] || "",
            parse: (v) => this.parse(v),
        });
    }

    get sources() {
        return [
            {
                options: async (request) => {
                    if (request.length > 5) {
                        const suggestions = await googlePlacesSession.getAddressPropositions({
                            partial_address: request,
                            use_employees_key: true,
                        });
                        suggestions.results = suggestions.results.map((result) => ({
                            label: result.formatted_address,
                            onSelect: () => this.selectAddressProposition(result),
                        }));
                        if (suggestions.results.length) {
                            suggestions.results.push({
                                label: "&#160;",
                                cssClass: "pe-none o-google-credits",
                            });
                        }
                        return suggestions.results;
                    } else {
                        return [];
                    }
                },
                optionSlot: "option",
                placeholder: _t("Searching for addresses..."),
            },
        ];
    }

    async selectAddressProposition(option) {
        const address = await googlePlacesSession.getAddressDetails({
            address: option.formatted_address,
            google_place_id: option.google_place_id,
            use_employees_key: true,
        });

        const fieldToDetail = {
            street: "formatted_street_number",
            country_id: "country",
            state_id: "state",
        };
        const fieldsToUpdate = Object.keys(standardAddressFields);

        const activeFields = this.props.record.activeFields;
        const fields = this.props.record.fields;
        const addressFieldMap = this.props.addressFieldMap;

        const valuesToUpdate = {};
        const rest = [];
        fieldsToUpdate.forEach((fieldName) => {
            const addressField = fieldToDetail[fieldName] || fieldName;
            let value = address[addressField];

            const recordFieldName = addressFieldMap[fieldName] || fieldName;
            if (recordFieldName in activeFields) {
                if (fields[recordFieldName].type === "many2one") {
                    value = value && { id: value[0], display_name: value[1] };
                } else if (Array.isArray(value)) {
                    value = value[1];
                }
                valuesToUpdate[recordFieldName] = value || false;
            } else if (!(recordFieldName in fields)) {
                value = Array.isArray(value) ? value[1] : value;
                rest.push(value);
            }
        });
        if (!(this.props.name in valuesToUpdate) && rest.length) {
            valuesToUpdate[this.props.name] = rest.join(" ");
        }
        this.props.record.update(valuesToUpdate);
    }
}

export const addressAutoComplete = {
    ...charField,
    component: AddressAutoComplete,
    displayName: _t("Address AutoComplete"),
    supportedTypes: ["char"],
    supportedOptions: [
        ...charField.supportedOptions,
        ...Object.entries(standardAddressFields).map(([fname, data]) => {
            return {
                label: data.label,
                placeholder: fname,
                type : "field",
                name: fname,
                availableTypes: data.type,
            }
        })
    ],
    extractProps: (fieldInfo, dynamicInfo) => {
        const { options } = fieldInfo;
        const props = charField.extractProps(fieldInfo, dynamicInfo);
        const addressFieldMap = {};
        Object.keys(standardAddressFields).forEach((fname) => {
            const optionValue = options[fname];
            if (optionValue) {
                addressFieldMap[fname] = optionValue;
            }
        });
        props.addressFieldMap = addressFieldMap;
        return props;
    }
};
registry.category("fields").add("google_address_autocomplete", addressAutoComplete);
