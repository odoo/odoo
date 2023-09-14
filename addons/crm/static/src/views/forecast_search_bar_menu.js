/** @odoo-module **/

import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";

export class ForecastSearchBarMenu extends SearchBarMenu {
    get filterItems() {
        if (!this.env.searchModel.hideTemporalFilter) {
            return super.filterItems;
        }
        return super.filterItems.filter(filter => !filter.crmTemporalFilter);
    }
}
