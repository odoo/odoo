import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { SearchBar } from "@web/search/search_bar/search_bar";

patch(SearchBar.prototype, {
    getPreposition(searchItem) {
        let preposition = super.getPreposition(searchItem);
        if (
            this.fields[searchItem.fieldName].name === 'payment_date'
            || this.fields[searchItem.fieldName].name === 'next_payment_date'
        ) {
            preposition = _t("until");
        }
        return preposition
    }
});
