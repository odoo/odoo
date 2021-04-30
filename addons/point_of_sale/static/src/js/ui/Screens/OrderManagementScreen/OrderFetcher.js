/** @odoo-module alias=point_of_sale.OrderFetcher **/

import { isRpcError } from 'point_of_sale.utils';
import { _t } from 'web.core';
import env from 'web.env';

class OrderFetcher {
    constructor(model) {
        this.model = model;
        this.currentPage = 1;
        this.ordersToShow = [];
        this.totalCount = 0;
        this.nPerPage = 15;
        this.searchDomain = undefined;
    }
    get activeOrders() {
        const pred = this.searchDomain ? this._predicateBasedOnSearchDomain.bind(this) : () => true;
        return this.model.getDraftOrders().filter(pred);
    }
    _predicateBasedOnSearchDomain(order) {
        const check = (order, field, searchWord) => {
            searchWord = searchWord.toLowerCase();
            switch (field) {
                case 'pos_reference':
                    return this.model.getOrderName(order).toLowerCase().includes(searchWord);
                case 'partner_id.display_name':
                    const client = this.model.getCustomer(order);
                    return client ? client.name.toLowerCase().includes(searchWord) : false;
                case 'date_order':
                    return moment(order.date_order).format('YYYY-MM-DD hh:mm A').includes(searchWord);
                default:
                    return false;
            }
        };
        for (let [field, _, searchWord] of (this.searchDomain || []).filter((item) => item !== '|')) {
            // remove surrounding "%" from `searchWord`
            searchWord = searchWord.substring(1, searchWord.length - 1);
            if (check(order, field, searchWord)) {
                return true;
            }
        }
        return false;
    }
    get nActiveOrders() {
        return this.activeOrders.length;
    }
    get lastPageFullOfActiveOrders() {
        return Math.trunc(this.nActiveOrders / this.nPerPage);
    }
    get remainingActiveOrders() {
        return this.nActiveOrders % this.nPerPage;
    }
    /**
     * for nPerPage = 10
     * +--------+----------+
     * | nItems | lastPage |
     * +--------+----------+
     * |     2  |       1  |
     * |    10  |       1  |
     * |    11  |       2  |
     * |    30  |       3  |
     * |    35  |       4  |
     * +--------+----------+
     */
    get lastPage() {
        const nItems = this.nActiveOrders + this.totalCount;
        const npages = nItems / this.nPerPage;
        if (this.model.floatEQ(npages, Math.trunc(npages))) {
            return Math.round(npages);
        } else {
            return Math.trunc(npages + 1);
        }
    }
    /**
     * Calling this methods populates the `ordersToShow` then trigger `update` event.
     * @related get
     *
     * NOTE: This is tightly-coupled with pagination. So if the current page contains all
     * active orders, it will not fetch anything from the server but only sets `ordersToShow`
     * to the active orders that fits the current page.
     */
    async fetch() {
        try {
            let limit, offset;
            let start, end;
            if (this.model.floatLTE(this.currentPage, this.lastPageFullOfActiveOrders)) {
                // Show only active orders.
                start = (this.currentPage - 1) * this.nPerPage;
                end = this.currentPage * this.nPerPage;
                this.ordersToShow = this.activeOrders.slice(start, end);
            } else if (this.model.floatEQ(this.currentPage, this.lastPageFullOfActiveOrders + 1)) {
                // Show partially the remaining active orders and
                // some orders from the backend.
                offset = 0;
                limit = this.nPerPage - this.remainingActiveOrders;
                start = (this.currentPage - 1) * this.nPerPage;
                end = this.nActiveOrders;
                this.ordersToShow = [...this.activeOrders.slice(start, end), ...(await this._fetch(limit, offset))];
            } else {
                // Show orders from the backend.
                offset =
                    this.nPerPage -
                    this.remainingActiveOrders +
                    (this.currentPage - (this.lastPageFullOfActiveOrders + 1) - 1) * this.nPerPage;
                limit = this.nPerPage;
                this.ordersToShow = await this._fetch(limit, offset);
            }
        } catch (error) {
            if (isRpcError(error) && error.message.code < 0) {
                this.model.ui.askUser('ErrorPopup', {
                    title: _t('Network Error'),
                    body: _t('Unable to fetch orders if offline.'),
                });
            } else {
                throw error;
            }
        }
    }
    /**
     * This returns the orders from the backend that needs to be shown.
     * If the order is already in cache, the full information about that
     * order is not fetched anymore, instead, we use info from cache.
     *
     * @param {number} limit
     * @param {number} offset
     */
    async _fetch(limit, offset) {
        const { ids, totalCount } = await this._getOrderIdsForCurrentPage(limit, offset);
        const idsNotInCache = ids.filter((id) => !this.model.exists('pos.order', id));
        if (idsNotInCache.length > 0) {
            const { data, closed_orders } = await this._fetchOrders(idsNotInCache);
            // Cache these fetched orders so that next time, no need to fetch
            // them again, unless invalidated. See `invalidateCache`.
            this.model.loadManagementOrders(data, new Set(closed_orders));
        }
        this.totalCount = totalCount;
        return ids.map((id) => this.model.getRecord('pos.order', id));
    }
    async _getOrderIdsForCurrentPage(limit, offset) {
        const config_id = this.model.config.id;
        return await this.model._rpc({
            model: 'pos.order',
            method: 'search_paid_order_ids',
            kwargs: { config_id, domain: this.searchDomain ? this.searchDomain : [], limit, offset },
            context: env.session.user_context,
        });
    }
    async _fetchOrders(ids) {
        return await this.model._rpc({
            model: 'pos.order',
            method: 'export_for_ui',
            args: [ids],
            context: env.session.user_context,
        });
    }
    async nextPage() {
        if (this.model.floatLT(this.currentPage, this.lastPage)) {
            this.currentPage += 1;
            await this.fetch();
        }
    }
    async prevPage() {
        if (this.model.floatGT(this.currentPage, 1)) {
            this.currentPage -= 1;
            await this.fetch();
        }
    }
    async setSearchDomain(searchDomain) {
        this.searchDomain = searchDomain;
        this.currentPage = 1;
        await this.fetch();
    }
    async setNPerPage(val) {
        this.nPerPage = val;
        await this.fetch();
    }
    invalidateCache(ids) {
        for (let id of ids) {
            this.model.deleteOrder(id);
        }
    }
}

export default OrderFetcher;
