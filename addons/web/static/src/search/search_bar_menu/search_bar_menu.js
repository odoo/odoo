import { Component } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
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
import { _t } from "@web/core/l10n/translation";

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
        dropdownState: {
            type: Object,
            optional: true,
            shape: {
                isOpen: Boolean,
                open: Function,
                close: Function,
            },
        },
    };

    setup() {
        this.facet_icons = FACET_ICONS;
        // Filter
        this.dialogService = useService("dialog");
        // GroupBy
        const fields = [];
        for (const [fieldName, field] of Object.entries(this.env.searchModel.searchViewFields)) {
            if (this.validateField(fieldName, field)) {
                fields.push(Object.assign({ name: fieldName }, field));
            }
        }
        this.fields = sortBy(fields, "string");
        // Favorite
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

    get favorites() {
        return this.env.searchModel.getSearchItems(
            (searchItem) => searchItem.type === "favorite" && searchItem.userId !== false
        );
    }

    get sharedFavorites() {
        return this.env.searchModel.getSearchItems(
            (searchItem) => searchItem.type === "favorite" && searchItem.userId === false
        );
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

    openConfirmationDialog(itemId, userId) {
        const dialogProps = {
            title: _t("Warning"),
            body: userId
                ? _t("Are you sure that you want to remove this filter?")
                : _t("This filter is global and will be removed for everyone."),
            confirmLabel: _t("Delete Filter"),
            confirm: () => this.env.searchModel.deleteFavorite(itemId),
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }
}
