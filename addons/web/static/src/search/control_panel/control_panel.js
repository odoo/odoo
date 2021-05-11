/** @odoo-module **/

import { ComparisonMenu } from "../comparison_menu/comparison_menu";
import { FavoriteMenu } from "../favorite_menu/favorite_menu";
import { FilterMenu } from "../filter_menu/filter_menu";
import { GroupByMenu } from "../group_by_menu/group_by_menu";
import { SearchBar } from "../search_bar/search_bar";
import { useService } from "@web/core/service_hook";

const { Component } = owl;

const MAPPING = {
    filter: FilterMenu,
    groupBy: GroupByMenu,
    comparison: ComparisonMenu,
    favorite: FavoriteMenu,
};

export class ControlPanel extends Component {
    setup() {
        this.actionService = useService("action");
    }

    /**
     * @returns {Object}
     */
    get display() {
        const display = Object.assign(
            {
                "top-left": true,
                "top-right": true,
                "bottom-left": true,
                "bottom-right": true,
            },
            this.props.display
        );
        display.top = display["top-left"] || display["top-right"];
        display.bottom = display["bottom-left"] || display["bottom-right"];
        return display;
    }

    /**
     * @returns {Component[]}
     */
    get searchMenus() {
        const searchMenus = [];
        for (const key of this.env.searchModel.searchMenuTypes) {
            // look in display instead?
            if (
                key === "comparison" &&
                this.env.searchModel.getSearchItems((i) => i.type === "comparison").length === 0
            ) {
                continue;
            }
            searchMenus.push({ Component: MAPPING[key], key });
        }
        return searchMenus;
    }

    /**
     * Called when an element of the breadcrumbs is clicked.
     *
     * @param {string} jsId
     */
    onBreadcrumbClicked(jsId) {
        this.actionService.restore(jsId);
    }

    /**
     * Called when a view is clicked in the view switcher.
     *
     * @param {ViewType} viewType
     */
    onViewClicked(viewType) {
        this.actionService.switchView(viewType);
    }
}

ControlPanel.components = { ComparisonMenu, FavoriteMenu, FilterMenu, GroupByMenu, SearchBar };
ControlPanel.template = "web.ControlPanel";
// ControlPanel.props = {
//     breadcrumbs: { type: Array, element: { jsId: String, name: String }, optional: true },
//     display: { type: Object, optional: true },
//     displayName: { type: String, optional: true },
//     viewSwitcherEntries: {
//         type: Array,
//         element: {
//             type: Object,
//             shape: {
//                 active: { type: Boolean, optional: true },
//                 icon: String,
//                 multiRecord: { type: Boolean, optional: true },
//                 name: [Object, String],
//                 type: String,
//             },
//         },
//         optional: true,
//     },
// };
ControlPanel.defaultProps = {
    breadcrumbs: [],
    display: {},
};
