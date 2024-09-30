/** @odoo-module **/

import { ExtendedAutocomplete } from "./extended_autocomplete";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { CharField, charField } from "@web/views/fields/char/char_field";

export class AddressAutoComplete extends CharField {
    static template = "address_autocomplete.AddressAutoCompleteTemplate";
    static components = { ExtendedAutocomplete, ...CharField };

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
                        return suggestions.results;
                    } else {
                        return [];
                    }
                },
                optionTemplate: "address_autocomplete.CharFieldDropdownOption",
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
            if (this.env.model.config.fields[field]) {
                // If field exists in config, add it to the dict
                dict[field] =
                    address[field] || (field === "country_id" || field === "state_id" ? false : "");
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
registry.category("fields").add("address_autocomplete", addressAutoComplete);
