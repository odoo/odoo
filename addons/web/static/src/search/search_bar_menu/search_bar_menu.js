// @ts-check

/** @module @web/search/search_bar_menu/search_bar_menu - Dropdown menu grouping Filter, Group By, Favorites, and search panels */

import { Component, useState } from "@odoo/owl";
import { AccordionItem } from "@web/components/dropdown/accordion_item";
import { CheckboxItem } from "@web/components/dropdown/checkbox_item";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { sortBy } from "@web/core/utils/collections/arrays";
import { useBus, useService } from "@web/core/utils/hooks";
import { CustomGroupByItem } from "@web/search/custom_group_by_item/custom_group_by_item";
import { PropertiesGroupByItem } from "@web/search/properties_group_by_item/properties_group_by_item";
import { FACET_ICONS, GROUPABLE_TYPES } from "@web/search/utils/misc";

const favoriteMenuRegistry = registry.category("favoriteMenu");

/**
 * Dropdown menu that groups Filter, Group By, and Favorites panels.
 *
 * Renders within the search bar and provides the UI for toggling filters,
 * date filters, group-bys, custom group-bys, property group-bys,
 * favorites, and registry-provided favorite menu items.
 */
export class SearchBarMenu extends Component {
    static template = "web.SearchBarMenu";
    static components = {
        Dropdown,
        DropdownItem,
        CheckboxItem,
        CustomGroupByItem,
        AccordionItem,
        PropertiesGroupByItem,
    };
    static props = {
        slots: {
            type: Object,
            optional: true,
            shape: {
                default: { optional: true },
            },
        },
        dropdownState: { ...Dropdown.props.state },
    };

    setup() {
        this.facet_icons = FACET_ICONS;
        // Filter
        this.actionService = useService("action");
        // GroupBy
        const fields = [];
        for (const [fieldName, field] of Object.entries(
            this.env.searchModel.searchViewFields,
        )) {
            if (this.validateField(fieldName, field)) {
                fields.push(Object.assign({ name: fieldName }, field));
            }
        }
        this.fields = sortBy(fields, "string");
        // Favorite
        this.state = useState({ sharedFavoritesExpanded: false });
        useBus(this.env.searchModel, "update", /** @type {any} */ (this.render));
    }

    // Filter Panel
    /** @returns {Object[]} enriched filter and dateFilter search items */
    get filterItems() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["filter", "dateFilter"].includes(searchItem.type),
        );
    }

    async onAddCustomFilterClick() {
        this.env.searchModel.spawnCustomFilterDialog();
    }

    /**
     * @param {Object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onFilterSelected({ itemId, optionId }) {
        if (optionId) {
            this.env.searchModel.toggleDateFilter(itemId, optionId);
        } else {
            this.env.searchModel.toggleSearchItem(itemId);
        }
    }

    // GroupBy Panel
    /**
     * @returns {boolean}
     */
    get hideCustomGroupBy() {
        return this.env.searchModel.hideCustomGroupBy || false;
    }

    /**
     * @returns {Object[]}
     */
    get groupByItems() {
        return this.env.searchModel.getSearchItems(
            (searchItem) =>
                ["groupBy", "dateGroupBy"].includes(searchItem.type) &&
                !searchItem.isProperty,
        );
    }

    /**
     * @param {string} fieldName
     * @param {Object} field
     * @returns {boolean}
     */
    validateField(fieldName, field) {
        const { groupable, type } = field;
        return groupable && fieldName !== "id" && GROUPABLE_TYPES.includes(type);
    }

    /**
     * @param {Object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onGroupBySelected({ itemId, optionId }) {
        if (optionId) {
            this.env.searchModel.toggleDateGroupBy(itemId, optionId);
        } else {
            this.env.searchModel.toggleSearchItem(itemId);
        }
    }

    /**
     * @param {string} fieldName
     */
    onAddCustomGroup(fieldName) {
        this.env.searchModel.createNewGroupBy(fieldName);
    }

    // Favorite Panel

    /** @returns {Object[]} private favorite search items (owned by current user) */
    get favorites() {
        return this.env.searchModel.getSearchItems(
            (searchItem) =>
                searchItem.type === "favorite" && searchItem.userIds.length === 1,
        );
    }

    /** @returns {Object[]} shared favorite search items (collapsed to 3 until expanded) */
    get sharedFavorites() {
        const sharedFavorites = this.env.searchModel.getSearchItems(
            (searchItem) =>
                searchItem.type === "favorite" && searchItem.userIds.length !== 1,
        );
        if (sharedFavorites.length <= 4 || this.state.sharedFavoritesExpanded) {
            this.state.sharedFavoritesExpanded = true;
        } else {
            sharedFavorites.length = 3;
        }
        return sharedFavorites;
    }

    /** @returns {{ Component: Function, groupNumber: number, key: string }[]} registry-provided favorite menu items */
    get otherItems() {
        const registryMenus = [];
        for (const item of favoriteMenuRegistry.getAll()) {
            if ("isDisplayed" in item ? item.isDisplayed(this.env) : true) {
                registryMenus.push({
                    Component: item.Component,
                    groupNumber: item.groupNumber,
                    key: item.Component.name,
                });
            }
        }
        return registryMenus;
    }

    /** @param {number} itemId */
    onFavoriteSelected(itemId) {
        this.env.searchModel.toggleSearchItem(itemId);
    }

    /** @param {number} itemId */
    editFavorite(itemId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "ir.filters",
            views: [[false, "form"]],
            context: {
                form_view_ref: "base.ir_filters_view_edit_form",
            },
            res_id: this.env.searchModel.searchItems[itemId].serverSideId,
        });
    }
}
