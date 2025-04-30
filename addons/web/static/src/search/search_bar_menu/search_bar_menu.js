import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { PropertiesGroupByItem } from "@web/search/properties_group_by_item/properties_group_by_item";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { sortBy } from "@web/core/utils/arrays";
import { useBus, useService } from "@web/core/utils/hooks";
import { AccordionItem } from "@web/core/dropdown/accordion_item";
import { CustomGroupByItem } from "@web/search/custom_group_by_item/custom_group_by_item";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { FACET_ICONS, GROUPABLE_TYPES } from "@web/search/utils/misc";

const favoriteMenuRegistry = registry.category("favoriteMenu");

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
        for (const [fieldName, field] of Object.entries(this.env.searchModel.searchViewFields)) {
            if (this.validateField(fieldName, field)) {
                fields.push(Object.assign({ name: fieldName }, field));
            }
        }
        this.fields = sortBy(fields, "string");
        // Favorite
        this.state = useState({ sharedFavoritesExpanded: false });
        useBus(this.env.searchModel, "update", this.render);
    }

    // Filter Panel
    get filterItems() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["filter", "dateFilter"].includes(searchItem.type)
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
                ["groupBy", "dateGroupBy"].includes(searchItem.type) && !searchItem.isProperty
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

    get favorites() {
        return this.env.searchModel.getSearchItems(
            (searchItem) => searchItem.type === "favorite" && searchItem.userIds.length === 1
        );
    }

    get sharedFavorites() {
        const sharedFavorites = this.env.searchModel.getSearchItems(
            (searchItem) => searchItem.type === "favorite" && searchItem.userIds.length !== 1
        );
        if (sharedFavorites.length <= 4 || this.state.sharedFavoritesExpanded) {
            this.state.sharedFavoritesExpanded = true;
        } else {
            sharedFavorites.length = 3;
        }
        return sharedFavorites;
    }

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

    onFavoriteSelected(itemId) {
        this.env.searchModel.toggleSearchItem(itemId);
    }

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
