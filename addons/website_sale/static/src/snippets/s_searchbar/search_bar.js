import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@website/snippets/s_searchbar/search_bar";

patch(SearchBar.prototype, {
    /**
     * @override
     */
    getFieldsNames() {
        return [...super.getFieldsNames(), "price", "list_price", "breadcrumb"];
    },
})
