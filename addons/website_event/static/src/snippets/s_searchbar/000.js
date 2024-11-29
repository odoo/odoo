import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@website/snippets/s_searchbar/000";

patch(SearchBar.prototype, {
    getFieldsNames() {
        return [...super.getFieldsNames(), "address_name"];
    }
});
