/** @odoo-module **/

import { Component } from "@odoo/owl";
import { DomainSelectorDialog } from "../../core/domain_selector_dialog/domain_selector_dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { SearchDropdownItem } from "@web/search/search_dropdown_item/search_dropdown_item";
import { FACET_ICONS } from "../utils/misc";
import { useBus, useService } from "@web/core/utils/hooks";
import { useGetDefaultLeafDomain } from "@web/core/domain_selector/utils";
import { _t } from "@web/core/l10n/translation";

export class FilterMenu extends Component {
    setup() {
        this.icon = FACET_ICONS.filter;
        this.dialogService = useService("dialog");
        this.getDefaultLeafDomain = useGetDefaultLeafDomain();
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

    async onAddCustomFilterClick() {
        const { domainEvalContext: context, resModel } = this.env.searchModel;
        const domain = await this.getDefaultLeafDomain(resModel);
        this.dialogService.add(DomainSelectorDialog, {
            resModel,
            defaultConnector: "|",
            domain,
            context,
            onConfirm: (domain) => this.env.searchModel.splitAndAddDomain(domain),
            disableConfirmButton: (domain) => domain === `[]`,
            title: _t("Add Custom Filter"),
            confirmButtonText: _t("Add"),
            discardButtonText: _t("Cancel"),
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
}

FilterMenu.components = { Dropdown, DropdownItem, SearchDropdownItem };
FilterMenu.template = "web.FilterMenu";
FilterMenu.props = {
    class: { type: String, optional: true },
};
