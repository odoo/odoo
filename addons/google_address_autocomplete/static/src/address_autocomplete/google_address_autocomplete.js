import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { googlePlacesSession } from "../google_places_session";

export class AddressAutoComplete extends CharField {
    static template = "google_address_autocomplete.AddressAutoCompleteTemplate";
    static components = { AutoComplete, ...CharField };

    get sources() {
        return [
            {
                options: async (request) => {
                    if (request.length > 5) {
                        const suggestions = await googlePlacesSession.getAddressPropositions({
                            partial_address: request,
                        });
                        if (suggestions.results.length) {
                            suggestions.results.push({
                                id: "credits",
                                classList: "pe-none o_google_credits",
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
        const address = await googlePlacesSession.getAddressDetails({
            address: option.formatted_address,
            google_place_id: option.google_place_id,
        });

        const dict = { [this.props.name]: address.formatted_street_number || "" };
        const fieldsToUpdate = ["street2", "city", "zip", "country_id", "state_id"];

        fieldsToUpdate.forEach((field) => {
            if (this.props.record.fields[field]) {
                // If field exists in record, add it to the dict
                if (field === "country_id") {
                    dict[field] = address["country"] || false;
                } else if (field === "state_id") {
                    dict[field] = address["state"] || false;
                } else {
                    dict[field] = address[field] || "";
                }
            }
        });
        this.props.record.update(dict);
    }
}

export const addressAutoComplete = {
    ...charField,
    component: AddressAutoComplete,
    displayName: _t("Address AutoComplete"),
    supportedTypes: ["char"],
};
registry.category("fields").add("google_address_autocomplete", addressAutoComplete);
