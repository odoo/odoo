import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@website/snippets/s_searchbar/search_bar";

patch(SearchBar.prototype, {
    /**
     * @override
     */
    getFieldsNames() {
        return [...super.getFieldsNames(), 'partner_name'];
    },
});
