/** @odoo-module */

import { Gui } from "@point_of_sale/js/Gui";

const { EventBus } = owl;

class SaleOrderFetcher extends EventBus {
    constructor() {
        super();
        this.currentPage = 1;
        this.ordersToShow = [];
        this.totalCount = 0;
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
        const nItems = this.totalCount;
        return Math.trunc(nItems / (this.nPerPage + 1)) + 1;
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
        // Show orders from the backend.
        const offset = this.nPerPage + (this.currentPage - 1 - 1) * this.nPerPage;
        const limit = this.nPerPage;
        this.ordersToShow = await this._fetch(limit, offset);

        this.trigger("update");
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
        const sale_orders = await this._getOrderIdsForCurrentPage(limit, offset);

        this.totalCount = sale_orders.length;
        return sale_orders;
    }
    async _getOrderIdsForCurrentPage(limit, offset) {
        const domain = [["currency_id", "=", this.comp.env.pos.currency.id]].concat(
            this.searchDomain || []
        );
        const saleOrders = await this.rpc({
            model: "sale.order",
            method: "search_read",
            args: [
                domain,
                [
                    "name",
                    "partner_id",
                    "amount_total",
                    "date_order",
                    "state",
                    "user_id",
                    "amount_unpaid",
                ],
                offset,
                limit,
            ],
            context: this.comp.env.session.user_context,
        });

        const saleOrderIds = saleOrders.flatMap((saleOrder) => saleOrder.id);
        const saleOrdersAmountUnpaid = await this.rpc({
            model: "sale.order",
            method: "get_order_amount_unpaid",
            args: [saleOrderIds],
            context: this.comp.env.session.user_context,
        });
        for (const saleOrder of saleOrders) {
            saleOrder.amount_unpaid = saleOrdersAmountUnpaid[saleOrder.id];
        }

        return saleOrders;
    }

    nextPage() {
        if (this.currentPage < this.lastPage) {
            this.currentPage += 1;
            this.fetch();
        }
    }
    prevPage() {
        if (this.currentPage > 1) {
            this.currentPage -= 1;
            this.fetch();
        }
    }
    /**
     * @param {integer|undefined} id id of the cached order
     * @returns {Array<models.Order>}
     */
    get(id) {
        return this.ordersToShow;
    }
    setSearchDomain(searchDomain) {
        this.searchDomain = searchDomain;
    }
    setComponent(comp) {
        this.comp = comp;
        return this;
    }
    setNPerPage(val) {
        this.nPerPage = val;
    }
    setPage(page) {
        this.currentPage = page;
    }

    async rpc() {
        Gui.setSyncStatus("connecting");
        const result = await this.comp.rpc(...arguments);
        Gui.setSyncStatus("connected");
        return result;
    }
}

export default new SaleOrderFetcher();
