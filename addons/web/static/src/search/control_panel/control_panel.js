/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { ComparisonMenu } from "../comparison_menu/comparison_menu";
import { FavoriteMenu } from "../favorite_menu/favorite_menu";
import { FilterMenu } from "../filter_menu/filter_menu";
import { GroupByMenu } from "../group_by_menu/group_by_menu";
import { SearchBar } from "../search_bar/search_bar";

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
     * !!! What follows is a hack, do not copy it !!!
     *
     * Duplicates the slots defined for the parent s.t. they are also available
     * for the current control panel.
     *
     * This hack is necessary since Owl does not support manual slots
     * assignment/transfer yet. This must be removed as soon as Owl implements
     * such a system.
     *
     * @strongly_discouraged_override
     */
    __render() {
        const { slots } = this.env.qweb.constructor;
        const { __owl__ } = this;
        const originalSlots = {};
        const transferredSlotNames = [
            "control-panel-top-left",
            "control-panel-top-right",
            "control-panel-bottom-left",
            "control-panel-bottom-right",
        ];
        for (const slotName of transferredSlotNames) {
            const parentSlotkey = `${__owl__.parent.__owl__.slotId}_${slotName}`;
            if (parentSlotkey in slots) {
                const cpSlotKey = `${__owl__.slotId}_${slotName}`;
                originalSlots[cpSlotKey] = slots[cpSlotKey];
                slots[cpSlotKey] = function (scope, extra) {
                    slots[parentSlotkey].call(this, __owl__.parent.__owl__.scope, extra);
                };
            }
        }
        const res = super.__render(...arguments);
        // Clean up
        Object.assign(slots, originalSlots);
        return res;
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

ControlPanel.components = { ComparisonMenu, FavoriteMenu, FilterMenu, GroupByMenu, SearchBar };
ControlPanel.template = "web.ControlPanel";
