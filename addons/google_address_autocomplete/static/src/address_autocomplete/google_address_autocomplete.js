import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class AddressAutoComplete extends CharField {
    static template = "google_address_autocomplete.AddressAutoCompleteTemplate";
    static components = { AutoComplete, ...CharField };

    setup() {
        this.sessionId = this._generateUUID();
    }

    /**
     * Used to generate a unique session ID for the places API.
     *
     * @private
     */
    _generateUUID() {
        return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
            const r = (Math.random() * 16) | 0,
                v = c == "x" ? r : (r & 0x3) | 0x8;
            return v.toString(16);
        });
    }

    get sources() {
        return [
            {
                options: async (request) => {
                    if (request.length > 5) {
                        const suggestions = await rpc("/autocomplete/address", {
                            partial_address: request,
                            session_id: this.sessionId || null,
                        });
                        if (suggestions.results.length) {
                            suggestions.results.push({
                                id: "credits",
                                classList: "pe-none",
                                type: "template",
                                name: "google_address_autocomplete.google_credits", 
                            })
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

    async onSelect(ev) {
        const address = await rpc("/autocomplete/address_full", {
            address: ev.formatted_address,
            google_place_id: ev.google_place_id,
            session_id: this.sessionId || null,
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
