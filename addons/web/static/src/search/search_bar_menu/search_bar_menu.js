/** @odoo-module **/

import { AdvancedSearchDialog } from "@web/search/filter_menu/advanced_search_dialog";
import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { sortBy } from "@web/core/utils/arrays";
import { useBus, useService } from "@web/core/utils/hooks";
import { CustomGroupByItem } from "@web/search/group_by_menu/custom_group_by_item";
import { SearchDropdownItem } from "@web/search/search_dropdown_item/search_dropdown_item";
import { FACET_ICONS, GROUPABLE_TYPES } from "@web/search/utils/misc";

const favoriteMenuRegistry = registry.category("favoriteMenu");

export class SearchBarMenu extends Component {
    static template = "web.SearchBarMenu";
    static components = {
        Dropdown,
        DropdownItem,
        SearchDropdownItem,
        CustomGroupByItem,
    };
    static props = {};

    setup() {
        this.facet_icons = FACET_ICONS;
        // Filter
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        // GroupBy
        const fields = [];
        for (const [fieldName, field] of Object.entries(this.env.searchModel.searchViewFields)) {
            if (this.validateField(fieldName, field)) {
                fields.push(Object.assign({ name: fieldName }, field));
            }
        }
        this.fields = sortBy(fields, "string");
        // Favorite
        this.dialogService = useService("dialog");

        useBus(this.env.searchModel, "update", this.render);
    }

    // Filter Panel
    get filterItems() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["filter", "dateFilter"].includes(searchItem.type)
        );
    }

    onAdvancedSearchClick() {
        const domains = [this.env.searchModel._getDomain({ withGlobal: false })];
        if (this.env.searchModel.comparison && !this.env.searchModel.globalComparison) {
            const { range } = this.env.searchModel.getFullComparison();
            domains.push(range);
        }
        const domain = Domain.and(domains).toString();
        this.dialogService.add(AdvancedSearchDialog, {
            domain,
            onConfirm: (domain) => this.onConfirm(domain),
            resModel: this.env.searchModel.resModel,
            isDebugMode: !!this.env.debug,
        });
    }

    async onConfirm(domain) {
        const isValid = await this.env.searchModel.isValidDomain(domain);
        if (!isValid) {
            this.notification.add(this.env._t("Domain is invalid. Please correct it"), {
                type: "danger",
            });
            return false;
        }
        this.env.searchModel.createAdvancedDomain(domain);
        return true;
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
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["groupBy", "dateGroupBy"].includes(searchItem.type)
        );
    }

    /**
     * @param {string} fieldName
     * @param {Object} field
     * @returns {boolean}
     */
    validateField(fieldName, field) {
        const { sortable, store, type } = field;
        return (
            (type === "many2many" ? store : sortable) &&
            fieldName !== "id" &&
            GROUPABLE_TYPES.includes(type)
        );
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

    // Comparison Panel
    get showComparisonMenu() {
        return (
            this.env.searchModel.searchMenuTypes.has("comparison") &&
            this.env.searchModel.getSearchItems((i) => i.type === "comparison").length > 0
        );
    }
    get comparisonItems() {
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

    // Favorite Panel
    /**
     * @returns {Array}
     */
    get favoriteItems() {
        const favorites = this.env.searchModel.getSearchItems(
            (searchItem) => searchItem.type === "favorite"
        );
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
        return [...favorites, ...registryMenus];
    }

    /**
     * @param {number} itemId
     */
    onFavoriteSelected(itemId) {
        this.env.searchModel.toggleSearchItem(itemId);
    }

    /**
     * @param {number} itemId
     */
    openConfirmationDialog(itemId) {
        const { userId } = this.favoriteItems.find((item) => item.id === itemId);
        const dialogProps = {
            title: this.env._t("Warning"),
            body: userId
                ? this.env._t("Are you sure that you want to remove this filter?")
                : this.env._t(
                      "This filter is global and will be removed for everybody if you continue."
                  ),
            confirm: () => this.env.searchModel.deleteFavorite(itemId),
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }
}
