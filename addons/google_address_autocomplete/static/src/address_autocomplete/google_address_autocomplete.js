import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { googlePlacesSession } from "../google_places_session";
import { useChildRef } from "@web/core/utils/hooks";
import { useInputField } from "@web/views/fields/input_field_hook";

export class AddressAutoComplete extends CharField {
    static template = "google_address_autocomplete.AddressAutoCompleteTemplate";
    static components = { AutoComplete, ...CharField.components };

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
                        if (suggestions.results.length) {
                            suggestions.results.push({
                                type: "credits",
                                classList: "pe-none o-google-credits",
                            });
                        }
                        return suggestions.results;
                    } else {
                        return [];
                    }
                },
                optionTemplate: "google_address_autocomplete.CharFieldDropdownOption",
                placeholder: _t("Searching for addresses..."),
            },
        ];
    }

    async onSelect(option) {
        if (option.type === "credits") {
            return;
        }
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
        const fieldsToUpdate = ["street", "street2", "city", "state_id", "zip", "country_id"];

        const activeFields = this.props.record.activeFields;
        const fields = this.props.record.fields;

        const valuesToUpdate = {};
        const rest = [];
        fieldsToUpdate.forEach((fieldName) => {
            const addressField = fieldToDetail[fieldName] || fieldName;
            let value = address[addressField];
            if (fieldName in activeFields) {
                valuesToUpdate[fieldName] = value || false;
            } else if (!(fieldName in fields)) {
                value = Array.isArray(value) ? value[1] : value;
                rest.push(value);
            }
        });
        if (!fieldsToUpdate.includes(this.props.name) && rest.length) {
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
};
registry.category("fields").add("google_address_autocomplete", addressAutoComplete);
