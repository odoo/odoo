/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { FACET_ICONS } from "../utils/misc";
import { useBus } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

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
     * @param {number} itemId
     */
    onComparisonSelected(itemId) {
        this.env.searchModel.toggleSearchItem(itemId);
    }
}

ComparisonMenu.template = "web.ComparisonMenu";
ComparisonMenu.components = { Dropdown, DropdownItem };
