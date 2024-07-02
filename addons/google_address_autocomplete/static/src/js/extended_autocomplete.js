/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class ExtendedAutocomplete extends AutoComplete {
    static props = {
        ...AutoComplete.props,
    };
    static template = "google_address_autocomplete.extended_autocomplete";
}
