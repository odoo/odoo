import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { PropertiesGroupByItem } from "@web/search/properties_group_by_item/properties_group_by_item";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { sortBy } from "@web/core/utils/arrays";
import { useBus, useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { useCommand } from "@web/core/commands/command_hook";
import { AccordionItem } from "@web/core/dropdown/accordion_item";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
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
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");

        // Add Share command
        if (this.env.config.actionId && !this.env.inDialog) {
            // TODO JESC FIXME BUG CLOSING SOME DIALOG (LIKE INVOICE), WRONG ACTIVE ELEMENT
            useCommand(_t("Share"), () => this.shareViewUrl(), {
                hotkey: "alt+shift+h",
                hotkeyOptions: { bypassEditableProtection: true },
            });
        }
    }

    // Filter Panel
    get filterItems() {
        return this.env.searchModel.getSearchItems((searchItem) =>
            ["filter", "dateFilter", "parentFilter"].includes(searchItem.type)
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
            this.env.searchModel.toggleParentFilter(itemId, optionId);
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

    /**
     * Adds encoded active filters to the current url and copies it to the user's
     * clipboard if possible. This url is parsed to reactivate filters if in route.
     */
    async shareViewUrl() {
        let shareUrl = browser.location.href;
        const extra = this.env.searchModel.generateQueryString();
        if (extra) {
            const [base, hash = ""] = browser.location.href.split("#");
            shareUrl = base + (base.includes("?") ? "&" : "?") + extra + (hash ? "#" + hash : "");
        }

        try {
            await navigator.clipboard.writeText(shareUrl);
        } catch {
            // Can fail in some context like if the browser is unsafe.
            this.dialogService.add(AlertDialog, {
                title: _t("Share the current view"),
                body: _t(
                    "You can use the link below to share the current view with its filters: \n\n %(url)s",
                    { url: shareUrl }
                ),
            });
            return;
        }

        const maxSafeUrlLength = 2000; // Chrome v.143. working up to 450000 chars and firefox > 500000 chars
        if (shareUrl.length < maxSafeUrlLength) {
            this.notificationService.add(_t("Link copied to clipboard"), { type: "success" });
        } else {
            this.notificationService.add(
                _t("Warning: Link copied to clipboard might be too long for some browsers"),
                { type: "warning" }
            );
        }
    }
}
