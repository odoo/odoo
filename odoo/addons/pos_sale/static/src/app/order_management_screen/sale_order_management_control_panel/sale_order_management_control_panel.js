/** @odoo-module */

import { useAutofocus, useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

// NOTE: These are constants so that they are only instantiated once
// and they can be used efficiently by the OrderManagementControlPanel.
const VALID_SEARCH_TAGS = new Set(["date", "customer", "client", "name", "order"]);
const FIELD_MAP = {
    date: "date_order",
    customer: "partner_id.complete_name",
    client: "partner_id.complete_name",
    name: "name",
    order: "name",
};
const SEARCH_FIELDS = ["name", "partner_id.complete_name", "date_order"];

/**
 * @emits search
 */
export class SaleOrderManagementControlPanel extends Component {
    static template = "pos_sale.SaleOrderManagementControlPanel";

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.saleOrderFetcher = useService("sale_order_fetcher");
        useAutofocus();

        const currentPartner = this.pos.get_order().get_partner();
        if (currentPartner) {
            this.pos.orderManagement.searchString = `"${currentPartner.name}"`;
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
     *      ['partner_id.complete_name', 'ilike', '%Customer 1%'],
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
     *      ['partner_id.complete_name', 'ilike', '%Steward%'],
     *      ['date_order', 'ilike', '%2020-05-01%']
     *   ]
     * ```
     */
    _computeDomain() {
        let domain = [
            ["state", "!=", "cancel"],
            ["invoice_status", "!=", "invoiced"],
        ];
        const input = this.pos.orderManagement.searchString.trim();
        if (!input) {
            return domain;
        }

        let searchConditions;
        let isQuoted = false;
        if (input.startsWith('"') && input.endsWith('"')) {
            searchConditions = [input.slice(1, -1)];
            isQuoted = true;
        } else {
            searchConditions = input.split(/[,&]\s*/);
        }

        if (searchConditions.length === 1) {
            const cond = searchConditions[0].split(/:\s*/);
            if (cond.length === 1 || isQuoted) {
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
        this.pos.orderManagement.searchString = "";
        this.onInputKeydown({ key: "Enter" });
    }
}
