/** @odoo-module **/

import { Pager } from "@web/core/pager/pager";
import { useService } from "@web/core/utils/hooks";
import { ComparisonMenu } from "../comparison_menu/comparison_menu";
import { FavoriteMenu } from "../favorite_menu/favorite_menu";
import { FilterMenu } from "../filter_menu/filter_menu";
import { GroupByMenu } from "../group_by_menu/group_by_menu";
import { SearchBar } from "../search_bar/search_bar";

const { Component, useState } = owl;

const MAPPING = {
    filter: FilterMenu,
    groupBy: GroupByMenu,
    comparison: ComparisonMenu,
    favorite: FavoriteMenu,
};

export class ControlPanel extends Component {
    setup() {
        this.actionService = useService("action");
        this.pagerProps = this.env.config.pagerProps
            ? useState(this.env.config.pagerProps)
            : undefined;
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
            this.props.display || this.env.searchModel.display.controlPanel
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

ControlPanel.components = {
    ComparisonMenu,
    FavoriteMenu,
    FilterMenu,
    GroupByMenu,
    Pager,
    SearchBar,
};
ControlPanel.template = "web.ControlPanel";
