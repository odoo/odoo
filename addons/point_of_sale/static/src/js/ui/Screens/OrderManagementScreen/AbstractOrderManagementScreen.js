/** @odoo-module alias=point_of_sale.AbstractOrderManagementScreen **/

import { useListener } from 'web.custom_hooks';
import PosComponent from 'point_of_sale.PosComponent';

const VALID_SEARCH_TAGS = new Set(['date', 'customer', 'client', 'name', 'order']);
const FIELD_MAP = {
    date: 'date_order',
    customer: 'partner_id.display_name',
    client: 'partner_id.display_name',
    name: 'pos_reference',
    order: 'pos_reference',
};
const SEARCH_FIELDS = ['pos_reference', 'partner_id.display_name', 'date_order'];

function getDomainForSingleCondition(fields, toSearch) {
    const orSymbols = Array(fields.length - 1).fill('|');
    return orSymbols.concat(fields.map((field) => [field, 'ilike', `%${toSearch}%`]));
}

class AbstractOrderManagementScreen extends PosComponent {
    constructor() {
        super(...arguments);
        useListener('click-order', this._onClickOrder);
        this.props.basicSearchBar.useSearchBar({
            onSearchTermChange: this._onSearch,
            placeholder: this.env._t('Search Orders...'),
            searchTerm: this.env.model.data.uiState.OrderManagementScreen.searchTerm,
        });
    }
    mounted() {
        // calculate how many can fit in the screen.
        // It is based on the height of the header element.
        // So the result is only accurate if each row is just single line.
        const flexContainer = this.el.querySelector('.flex-container');
        const cpEl = this.el.querySelector('.control-panel');
        const headerEl = this.el.querySelector('.order-row.header');
        const val = Math.trunc(
            (flexContainer.offsetHeight - cpEl.offsetHeight - headerEl.offsetHeight) / headerEl.offsetHeight
        );
        setTimeout(() => this.env.model.actionHandler({ name: 'actionsetNPerPage', args: [val] }), 0);
    }
    async _onClickOrder(event) {
        await this.env.model.actionHandler({ name: 'actionSelectOrder', args: [event.detail] });
    }
    get selectedClient() {
        const order = this.getActiveOrder();
        if (!order) return undefined;
        return this.env.model.getCustomer(order);
    }
    _onSearch([searchTerm, key]) {
        this.env.model.data.uiState.OrderManagementScreen.searchTerm = searchTerm;
        if ((key && key === 'Enter') || !key) {
            const domain = this._computeDomain(searchTerm.trim());
            this.env.model.actionHandler({ name: 'actionSearch', args: [domain] });
        }
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
     * @param {string} searchTerm
     */
    _computeDomain(searchTerm) {
        if (!searchTerm) return;
        const searchConditions = searchTerm.split(/[,&]\s*/);
        if (searchConditions.length === 1) {
            let cond = searchConditions[0].split(/:\s*/);
            if (cond.length === 1) {
                return getDomainForSingleCondition(SEARCH_FIELDS, cond[0]);
            }
        }
        const domain = [];
        for (let cond of searchConditions) {
            let [tag, value] = cond.split(/:\s*/);
            if (!VALID_SEARCH_TAGS.has(tag)) continue;
            domain.push([FIELD_MAP[tag], 'ilike', `%${value}%`]);
        }
        return domain;
    }
    getActiveOrder() {
        const orderId = this.env.model.data.uiState.OrderManagementScreen.activeOrderId;
        return this.env.model.getRecord('pos.order', orderId);
    }
}

export default AbstractOrderManagementScreen;
