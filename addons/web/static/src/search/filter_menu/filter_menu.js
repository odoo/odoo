/** @odoo-module **/

import { CustomFilterItem } from "./custom_filter_item";
import { FACET_ICONS } from "../utils/misc";
import { useBus } from "@web/core/utils/hooks";
import { SearchDropdownItem } from "@web/search/search_dropdown_item/search_dropdown_item";

const { Component } = owl;

export class FilterMenu extends Component {
    setup() {
        this.icon = FACET_ICONS.filter;

        useBus(this.env.searchModel, "update", this.render);
    }

    /**
     * @returns {Object[]}
     */
    get items() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["filter", "dateFilter"].includes(searchItem.type)
        );
    }

    /**
     * @param {CustomEvent} ev
     */
    onFilterSelected(ev) {
        const { itemId, optionId } = ev.detail.payload;
        if (optionId) {
            this.env.searchModel.toggleDateFilter(itemId, optionId);
        } else {
            this.env.searchModel.toggleSearchItem(itemId);
        }
    }
}

FilterMenu.components = { CustomFilterItem, DropdownItem: SearchDropdownItem };
FilterMenu.template = "web.FilterMenu";
