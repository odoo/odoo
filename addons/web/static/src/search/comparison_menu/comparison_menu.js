/** @odoo-module **/

import { FACET_ICONS } from "../utils/misc";
import { useBus } from "@web/core/utils/hooks";
import { SearchDropdownItem } from "@web/search/search_dropdown_item/search_dropdown_item";

const { Component } = owl;

export class ComparisonMenu extends Component {
    setup() {
        this.icon = FACET_ICONS.comparison;

        useBus(this.env.searchModel, "update", this.render);
    }

    /**
     * @returns {Object[]}
     */
    get items() {
        return this.env.searchModel.getSearchItems(
            (searchItem) => searchItem.type === "comparison"
        );
    }

    /**
     * @param {CustomEvent}
     */
    onComparisonSelected(ev) {
        const { itemId } = ev.detail.payload;
        this.env.searchModel.toggleSearchItem(itemId);
    }
}
ComparisonMenu.components = { DropdownItem: SearchDropdownItem };
ComparisonMenu.template = "web.ComparisonMenu";
