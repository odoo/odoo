/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@website/snippets/s_searchbar/search_bar";

// Fetch the original getFieldsNames method from SearchBar
const originalGetFieldsNames = SearchBar.prototype.getFieldsNames;

patch(SearchBar.prototype, {
    getFieldsNames() {
        const baseFields = originalGetFieldsNames ? originalGetFieldsNames.call(this) : [];
        return [...new Set([...baseFields, "barcode", "attributes"])];
    },
});
