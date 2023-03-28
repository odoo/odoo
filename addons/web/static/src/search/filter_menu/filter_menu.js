/** @odoo-module **/

import { AdvancedSearchDialog } from "./advanced_search_dialog";
import { Component } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SearchDropdownItem } from "@web/search/search_dropdown_item/search_dropdown_item";
import { FACET_ICONS } from "../utils/misc";
import { useBus, useService } from "@web/core/utils/hooks";

export class FilterMenu extends Component {
    setup() {
        this.icon = FACET_ICONS.filter;
        this.dialogService = useService("dialog");
        this.notification = useService("notification");
        useBus(this.env.searchModel, "update", this.render);
    }

    /**
     * @returns {Object[]}
     */
    get items() {
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
}

FilterMenu.components = { Dropdown, DropdownItem, SearchDropdownItem };
FilterMenu.template = "web.FilterMenu";
FilterMenu.props = {
    class: { type: String, optional: true },
};
