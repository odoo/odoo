/** @odoo-module */

import { useAutofocus, useService } from "@web/core/utils/hooks";
import { orderManagement } from "@point_of_sale/js/PosContext";
import { Component, useState } from "@odoo/owl";

// NOTE: These are constants so that they are only instantiated once
// and they can be used efficiently by the OrderManagementControlPanel.
const VALID_SEARCH_TAGS = new Set(["date", "customer", "client", "name", "order"]);
const FIELD_MAP = {
    date: "date_order",
    customer: "partner_id.display_name",
    client: "partner_id.display_name",
    name: "name",
    order: "name",
};
const SEARCH_FIELDS = ["name", "partner_id.display_name", "date_order"];

/**
 * @emits search
 */
export class SaleOrderManagementControlPanel extends Component {
    static template = "SaleOrderManagementControlPanel";

    setup() {
        super.setup();
        this.saleOrderFetcher = useService("sale_order_fetcher");
        this.orderManagementContext = useState(orderManagement);
        useAutofocus();

        const currentPartner = this.env.pos.get_order().get_partner();
        if (currentPartner) {
            this.orderManagementContext.searchString = currentPartner.name;
        }
        this.saleOrderFetcher.setSearchDomain(this._computeDomain());
    }
    onInputKeydown(event) {
        if (event.key === "Enter") {
            this.props.onSearch(this._computeDomain());
        }
    }
    get showPageControls() {
        return this.saleOrderFetcher.lastPage > 1;
    }
    get pageNumber() {
        const currentPage = this.saleOrderFetcher.currentPage;
        const lastPage = this.saleOrderFetcher.lastPage;
        return isNaN(lastPage) ? "" : `(${currentPage}/${lastPage})`;
    }
    get validSearchTags() {
        return VALID_SEARCH_TAGS;
    }
    get fieldMap() {
        return FIELD_MAP;
    }
    get searchFields() {
        return SEARCH_FIELDS;
    }
    /**
     * E.g. 1
     * ```
     *   searchString = 'Customer 1'
     *   result = [
     *      '|',
     *      '|',
     *      ['pos_reference', 'ilike', '%Customer 1%'],
     *      ['partner_id.display_name', 'ilike', '%Customer 1%'],
     *      ['date_order', 'ilike', '%Customer 1%']
     *   ]
     * ```
     *
     * E.g. 2
     * ```
     *   searchString = 'date: 2020-05'
     *   result = [
     *      ['date_order', 'ilike', '%2020-05%']
     *   ]
     * ```
     *
     * E.g. 3
     * ```
     *   searchString = 'customer: Steward, date: 2020-05-01'
     *   result = [
     *      ['partner_id.display_name', 'ilike', '%Steward%'],
     *      ['date_order', 'ilike', '%2020-05-01%']
     *   ]
     * ```
     */
    _computeDomain() {
        let domain = [
            ["state", "!=", "cancel"],
            ["invoice_status", "!=", "invoiced"],
        ];
        const input = this.orderManagementContext.searchString.trim();
        if (!input) {
            return domain;
        }

        const searchConditions = this.orderManagementContext.searchString.split(/[,&]\s*/);
        if (searchConditions.length === 1) {
            const cond = searchConditions[0].split(/:\s*/);
            if (cond.length === 1) {
                domain = domain.concat(Array(this.searchFields.length - 1).fill("|"));
                domain = domain.concat(
                    this.searchFields.map((field) => [field, "ilike", `%${cond[0]}%`])
                );
                return domain;
            }
        }

        for (const cond of searchConditions) {
            const [tag, value] = cond.split(/:\s*/);
            if (!this.validSearchTags.has(tag)) {
                continue;
            }
            domain.push([this.fieldMap[tag], "ilike", `%${value}%`]);
        }
        return domain;
    }
    clearSearch() {
        this.orderManagementContext.searchString = "";
        this.onInputKeydown({ key: "Enter" });
    }
}
