/** @odoo-module **/

import { FACET_ICONS } from "../utils/misc";
import { useBus } from "@web/core/utils/hooks";

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

ComparisonMenu.template = "web.ComparisonMenu";
