import { patch } from "@web/core/utils/patch";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { _t } from "@web/core/l10n/translation";

/**
 * Add team switcher dropdown menu in search bar
 */
patch(SearchBarMenu.prototype, {
    /**
     * @override
     * Hide team switcher filter item from the search bar menu.
     */
    get filterItems() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["filter", "dateFilter", "parentFilter", "lazyParentFilter"].includes(searchItem.type) &&
            searchItem.name !== this.env.searchModel.tsFilterName
        );
    },
    get tsAllTeamLabel() {
        return _t("All");
    },
    get tsFilterItem() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["parentFilter", "lazyParentFilter"].includes(searchItem.type) &&
            searchItem.name === this.env.searchModel.tsFilterName
        )?.[0];
    },
    get tsSelectedName() {
        return (
            this.tsFilterItem?.options.find((o) => o.id === this.tsSelectedOptionId)?.description ||
            this.tsAllTeamLabel
        );
    },
    get tsSelectedOptionId() {
        return this.env.searchModel.tsSelectedOptionId;
    },
});
