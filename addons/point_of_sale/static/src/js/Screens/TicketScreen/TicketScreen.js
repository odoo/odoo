odoo.define('point_of_sale.TicketScreen', function (require) {
    'use strict';

    const { Order } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const { useListener } = require("@web/core/utils/hooks");
    const { parse } = require('web.field_utils');

    const { onMounted, onWillUnmount, useState } = owl;

    class TicketScreen extends IndependentToOrderScreen {
        setup() {
            super.setup();
            useListener('close-screen', this._onCloseScreen);
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            useListener('click-order', this._onClickOrder);
            useListener('create-new-order', this._onCreateNewOrder);
            useListener('delete-order', this._onDeleteOrder);
            useListener('next-page', this._onNextPage);
            useListener('prev-page', this._onPrevPage);
            useListener('order-invoiced', this._onInvoiceOrder);
            useListener('click-order-line', this._onClickOrderline);
            useListener('click-refund-order-uid', this._onClickRefundOrderUid);
            useListener('update-selected-orderline', this._onUpdateSelectedOrderline);
            useListener('do-refund', this._onDoRefund);
            NumberBuffer.use({
                nonKeyboardInputEvent: 'numpad-click-input',
                triggerAtInput: 'update-selected-orderline',
            });
            this._state = this.env.pos.TICKET_SCREEN_STATE;
            this.state = useState({
                showSearchBar: !this.env.isMobile,
            });
            const defaultUIState = this.props.reuseSavedUIState
                ? this._state.ui
                : {
                      selectedSyncedOrderId: null,
                      searchDetails: this.env.pos.getDefaultSearchDetails(),
                      filter: null,
                      selectedOrderlineIds: {},
                  };
            Object.assign(this._state.ui, defaultUIState, this.props.ui || {});

            onMounted(this.onMounted);
            onWillUnmount(this.onWillUnmount);
        }
        //#region LIFECYCLE METHODS
        onMounted() {
            this.env.posbus.on('ticket-button-clicked', this, this.close);
            setTimeout(() => {
                // Show updated list of synced orders when going back to the screen.
                this._onFilterSelected({ detail: { filter: this._state.ui.filter } });
            });
        }
        onWillUnmount() {
            this.env.posbus.off('ticket-button-clicked', this);
        }
        //#endregion
        //#region EVENT HANDLERS
        _onCloseScreen() {
            this.close();
        }
        async _onFilterSelected(event) {
            this._state.ui.filter = event.detail.filter;
            if (this._state.ui.filter == 'SYNCED') {
                await this._fetchSyncedOrders();
            }
        }
        async _onSearch(event) {
            Object.assign(this._state.ui.searchDetails, event.detail);
            if (this._state.ui.filter == 'SYNCED') {
                this._state.syncedOrders.currentPage = 1;
                await this._fetchSyncedOrders();
            }
        }
        _onClickOrder({ detail: clickedOrder }) {
            if (!clickedOrder || clickedOrder.locked) {
                if (this._state.ui.selectedSyncedOrderId == clickedOrder.backendId) {
                    this._state.ui.selectedSyncedOrderId = null;
                } else {
                    this._state.ui.selectedSyncedOrderId = clickedOrder.backendId;
                }
                if (!this.getSelectedOrderlineId()) {
                    // Automatically select the first orderline of the selected order.
                    const firstLine = clickedOrder.get_orderlines()[0];
                    if (firstLine) {
                        this._state.ui.selectedOrderlineIds[clickedOrder.backendId] = firstLine.id;
                    }
                }
                NumberBuffer.reset();
            } else {
                this._setOrder(clickedOrder);
            }
        }
        _onCreateNewOrder() {
            this.env.pos.add_new_order();
            this.showScreen('ProductScreen');
        }
        _selectNextOrder(currentOrder) {
            const currentOrderIndex = this._getOrderList().indexOf(currentOrder);
            const orderList = this._getOrderList();
            this.env.pos.set_order(orderList[currentOrderIndex+1] || orderList[currentOrderIndex-1]);
        }
        async _onDeleteOrder({ detail: order }) {
            const screen = order.get_screen_data();
            if (['ProductScreen', 'PaymentScreen'].includes(screen.name) && order.get_orderlines().length > 0) {
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Existing orderlines'),
                    body: _.str.sprintf(
                      this.env._t('%s has a total amount of %s, are you sure you want to delete this order ?'),
                      order.name, this.getTotal(order)
                    ),
                });
                if (!confirmed) return;
            }
            if (order && (await this._onBeforeDeleteOrder(order))) {
                if (order === this.env.pos.get_order()) {
                    this._selectNextOrder(order);
                }
                this.env.pos.removeOrder(order);
            }
        }
        async _onNextPage() {
            if (this._state.syncedOrders.currentPage < this._getLastPage()) {
                this._state.syncedOrders.currentPage += 1;
                await this._fetchSyncedOrders();
            }
        }
        async _onPrevPage() {
            if (this._state.syncedOrders.currentPage > 1) {
                this._state.syncedOrders.currentPage -= 1;
                await this._fetchSyncedOrders();
            }
        }
        async _onInvoiceOrder({ detail: orderId }) {
            this.env.pos._invalidateSyncedOrdersCache([orderId]);
            await this._fetchSyncedOrders();
        }
        _onClickOrderline({ detail: orderline }) {
            const order = this.getSelectedSyncedOrder();
            this._state.ui.selectedOrderlineIds[order.backendId] = orderline.id;
            NumberBuffer.reset();
        }
        _onClickRefundOrderUid({ detail: orderUid }) {
            // Open the refund order.
            const refundOrder = this.env.pos.orders.find((order) => order.uid == orderUid);
            if (refundOrder) {
                this._setOrder(refundOrder);
            }
        }
        _onUpdateSelectedOrderline({ detail }) {
            const buffer = detail.buffer;
            const order = this.getSelectedSyncedOrder();
            if (!order) return NumberBuffer.reset();

            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
            if (!orderline) return NumberBuffer.reset();

            const toRefundDetail = this._getToRefundDetail(orderline);
            // When already linked to an order, do not modify the to refund quantity.
            if (toRefundDetail.destinationOrderUid) return NumberBuffer.reset();

            const refundableQty = toRefundDetail.orderline.qty - toRefundDetail.orderline.refundedQty;
            if (refundableQty <= 0) return NumberBuffer.reset();

            if (buffer == null || buffer == '') {
                toRefundDetail.qty = 0;
            } else {
                const quantity = Math.abs(parse.float(buffer));
                if (quantity > refundableQty) {
                    NumberBuffer.reset();
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Maximum Exceeded'),
                        body: _.str.sprintf(
                            this.env._t(
                                'The requested quantity to be refunded is higher than the ordered quantity. %s is requested while only %s can be refunded.'
                            ),
                            quantity,
                            refundableQty
                        ),
                    });
                } else {
                    toRefundDetail.qty = quantity;
                }
            }
        }
        async _onDoRefund() {
            const order = this.getSelectedSyncedOrder();

            if (this._doesOrderHaveSoleItem(order)) {
                if (!this._prepareAutoRefundOnOrder(order)) {
                    // Don't proceed on refund if preparation returned false.
                    return;
                }
            }

            if (!order) {
                this._state.ui.highlightHeaderNote = !this._state.ui.highlightHeaderNote;
                return;
            }

            const partner = order.get_partner();

            const allToRefundDetails = this._getRefundableDetails(partner);
            if (allToRefundDetails.length == 0) {
                this._state.ui.highlightHeaderNote = !this._state.ui.highlightHeaderNote;
                return;
            }

            // The order that will contain the refund orderlines.
            // Use the destinationOrder from props if the order to refund has the same
            // partner as the destinationOrder.
            const destinationOrder = this._setDestinationOrder(this.props.destinationOrder, partner);

            // Add orderline for each toRefundDetail to the destinationOrder.
            for (const refundDetail of allToRefundDetails) {
                const product = this.env.pos.db.get_product_by_id(refundDetail.orderline.productId);
                const options = this._prepareRefundOrderlineOptions(refundDetail);
                await destinationOrder.add_product(product, options);
                refundDetail.destinationOrderUid = destinationOrder.uid;
            }

            // Set the partner to the destinationOrder.
            if (partner && !destinationOrder.get_partner()) {
                destinationOrder.set_partner(partner);
                destinationOrder.updatePricelist(partner);
            }

            if (this.env.pos.get_order().cid !== destinationOrder.cid) {
                this.env.pos.set_order(destinationOrder);
            }

            this._onCloseScreen();
        }
         _setDestinationOrder(order, partner) {
            if (order && partner === this.props.destinationOrder.get_partner() && !this.env.pos.doNotAllowRefundAndSales()) {
                return order;
            } else if(this.env.pos.get_order() && !this.env.pos.get_order().orderlines.length) {
                return this.env.pos.get_order();
            }
            return this.env.pos.add_new_order({ silent: true });
        }
        //#endregion
        //#region PUBLIC METHODS
        close() {
            /**
             * Automatically create new order when there is no currently active order.
             * Important in fiscal modules to keep the sequence of the orders.
             */
            if (this.env.pos.orders.length == 0) {
                this.env.pos.add_new_order();
            }
            super.close();
        }
        getSelectedSyncedOrder() {
            if (this._state.ui.filter == 'SYNCED') {
                return this._state.syncedOrders.cache[this._state.ui.selectedSyncedOrderId];
            } else {
                return null;
            }
        }
        getSelectedOrderlineId() {
            return this._state.ui.selectedOrderlineIds[this._state.ui.selectedSyncedOrderId];
        }
        /**
         * Override to conditionally show the new ticket button.
         */
        shouldShowNewOrderButton() {
            return true;
        }
        getFilteredOrderList() {
            if (this._state.ui.filter == 'SYNCED') return this._state.syncedOrders.toShow;
            const filterCheck = (order) => {
                if (this._state.ui.filter && this._state.ui.filter !== 'ACTIVE_ORDERS') {
                    const screen = order.get_screen_data();
                    return this._state.ui.filter === this._getScreenToStatusMap()[screen.name];
                }
                return true;
            };
            const { fieldName, searchTerm } = this._state.ui.searchDetails;
            const searchField = this._getSearchFields()[fieldName];
            const searchCheck = (order) => {
                if (!searchField) return true;
                const repr = searchField.repr(order);
                if (repr === null) return true;
                if (!searchTerm) return true;
                return repr && repr.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (order) => {
                return filterCheck(order) && searchCheck(order);
            };
            return this._getOrderList().filter(predicate);
        }
        getDate(order) {
            return moment(order.validation_date).format('YYYY-MM-DD hh:mm A');
        }
        getTotal(order) {
            return this.env.pos.format_currency(order.get_total_with_tax());
        }
        getPartner(order) {
            return order.get_partner_name();
        }
        getCardholderName(order) {
            return order.get_cardholder_name();
        }
        getCashier(order) {
            return order.cashier ? order.cashier.name : '';
        }
        getStatus(order) {
            if (order.locked) {
                return this.env._t('Paid');
            } else {
                const screen = order.get_screen_data();
                return this._getOrderStates().get(this._getScreenToStatusMap()[screen.name]).text;
            }
        }
        /**
         * If the order is the only order and is empty
         */
        isDefaultOrderEmpty(order) {
            let status = this._getScreenToStatusMap()[order.get_screen_data().name];
            let productScreenStatus = this._getScreenToStatusMap().ProductScreen;
            return order.get_orderlines().length === 0 && this.env.pos.get_order_list().length === 1 &&
                status === productScreenStatus && order.get_paymentlines().length === 0;
        }
        /**
         * Hide the delete button if one of the payments is a 'done' electronic payment.
         */
        shouldHideDeleteButton(order) {
            return (
                this.isDefaultOrderEmpty(order)||
                order.locked ||
                order
                    .get_paymentlines()
                    .some((payment) => payment.is_electronic() && payment.get_payment_status() === 'done')
            );
        }
        isHighlighted(order) {
            if (this._state.ui.filter == 'SYNCED') {
                const selectedOrder = this.getSelectedSyncedOrder();
                return selectedOrder ? order.backendId == selectedOrder.backendId : false;
            } else {
                const activeOrder = this.env.pos.get_order();
                return activeOrder ? activeOrder.uid == order.uid : false;
            }
        }
        showCardholderName() {
            return this.env.pos.payment_methods.some((method) => method.use_payment_terminal);
        }
        getSearchBarConfig() {
            return {
                searchFields: new Map(
                    Object.entries(this._getSearchFields()).map(([key, val]) => [key, val.displayName])
                ),
                filter: { show: true, options: this._getFilterOptions() },
                defaultSearchDetails: this._state.ui.searchDetails,
                defaultFilter: this._state.ui.filter,
            };
        }
        shouldShowPageControls() {
            return this._state.ui.filter == 'SYNCED' && this._getLastPage() > 1;
        }
        getPageNumber() {
            if (!this._state.syncedOrders.totalCount) {
                return `1/1`;
            } else {
                return `${this._state.syncedOrders.currentPage}/${this._getLastPage()}`;
            }
        }
        getSelectedPartner() {
            const order = this.getSelectedSyncedOrder();
            return order ? order.get_partner() : null;
        }
        getHasItemsToRefund() {
            const order = this.getSelectedSyncedOrder();
            if (!order) return false;
            if (this._doesOrderHaveSoleItem(order)) return true;
            const total = Object.values(this.env.pos.toRefundLines)
                .filter(
                    (toRefundDetail) =>
                        toRefundDetail.orderline.orderUid === order.uid && !toRefundDetail.destinationOrderUid
                )
                .map((toRefundDetail) => toRefundDetail.qty)
                .reduce((acc, val) => acc + val, 0);
            return !this.env.pos.isProductQtyZero(total);
        }
        //#endregion
        //#region PRIVATE METHODS
        /**
         * Find the empty order with the following priority:
         * - The empty order with the same parter as the provided.
         * - The first empty order without a partner.
         * - If no empty order, create a new one.
         * @param {Object | null} partner
         * @returns {boolean}
         */
        _getEmptyOrder(partner) {
            let emptyOrderForPartner = null;
            let emptyOrder = null;
            for (const order of this.env.pos.orders) {
                if (order.get_orderlines().length === 0 && order.get_paymentlines().length === 0) {
                    if (order.get_partner() === partner) {
                        emptyOrderForPartner = order;
                        break;
                    } else if (!order.get_partner() && emptyOrder === null) {
                        // If emptyOrderForPartner is not found, we will use the first empty order.
                        emptyOrder = order;
                    }
                }
            }
            return emptyOrderForPartner || emptyOrder || this.env.pos.add_new_order();
        }
        _doesOrderHaveSoleItem(order) {
            const orderlines = order.get_orderlines();
            if (orderlines.length !== 1) return false;
            const theOrderline = orderlines[0];
            const refundableQty = theOrderline.get_quantity() - theOrderline.refunded_qty;
            return this.env.pos.isProductQtyZero(refundableQty - 1);
        }
        _prepareAutoRefundOnOrder(order) {
            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
            if (!orderline) return false;

            const toRefundDetail = this._getToRefundDetail(orderline);
            const refundableQty = orderline.get_quantity() - orderline.refunded_qty;
            if (this.env.pos.isProductQtyZero(refundableQty - 1)) {
                toRefundDetail.qty = 1;
            }
            return true;
        }
        /**
         * Returns the corresponding toRefundDetail of the given orderline.
         * SIDE-EFFECT: Automatically creates a toRefundDetail object for
         * the given orderline if it doesn't exist and returns it.
         * @param {models.Orderline} orderline
         * @returns
         */
        _getToRefundDetail(orderline) {
            if (orderline.id in this.env.pos.toRefundLines) {
                return this.env.pos.toRefundLines[orderline.id];
            } else {
                const partner = orderline.order.get_partner();
                const orderPartnerId = partner ? partner.id : false;
                const newToRefundDetail = {
                    qty: 0,
                    orderline: {
                        id: orderline.id,
                        productId: orderline.product.id,
                        price: orderline.price,
                        qty: orderline.quantity,
                        refundedQty: orderline.refunded_qty,
                        orderUid: orderline.order.uid,
                        orderBackendId: orderline.order.backendId,
                        orderPartnerId,
                        tax_ids: orderline.get_taxes().map(tax => tax.id),
                        discount: orderline.discount,
                    },
                    destinationOrderUid: false,
                };
                this.env.pos.toRefundLines[orderline.id] = newToRefundDetail;
                return newToRefundDetail;
            }
        }
        /**
         * Select the lines from toRefundLines, as they can come from different orders.
         * Returns only details that:
         * - The quantity to refund is not zero
         * - Filtered by partner (optional)
         * - It's not yet linked to an active order (no destinationOrderUid)
         *
         * @param {Object} partner (optional)
         * @returns {Array} refundableDetails
         */
        _getRefundableDetails(partner) {
            return Object.values(this.env.pos.toRefundLines).filter(
                ({ qty, orderline, destinationOrderUid }) =>
                    !this.env.pos.isProductQtyZero(qty) &&
                    (partner ? orderline.orderPartnerId == partner.id : true) &&
                    !destinationOrderUid
            );
        }
        /**
         * Prepares the options to add a refund orderline.
         *
         * @param {Object} toRefundDetail
         * @returns {Object}
         */
        _prepareRefundOrderlineOptions(toRefundDetail) {
            const { qty, orderline } = toRefundDetail;
            return {
                quantity: -qty,
                price: orderline.price,
                extras: { price_manually_set: true },
                merge: false,
                refunded_orderline_id: orderline.id,
                tax_ids: orderline.tax_ids,
                discount: orderline.discount,
            }
        }
        _setOrder(order) {
            this.env.pos.set_order(order);
            this.close();
        }
        _getOrderList() {
            return this.env.pos.get_order_list();
        }
        _getFilterOptions() {
            const orderStates = this._getOrderStates();
            orderStates.set('SYNCED', { text: this.env._t('Paid') });
            return orderStates;
        }
        /**
         * @returns {Record<string, { repr: (order: models.Order) => string, displayName: string, modelField: string }>}
         */
        _getSearchFields() {
            const fields = {
                RECEIPT_NUMBER: {
                    repr: (order) => order.name,
                    displayName: this.env._t('Receipt Number'),
                    modelField: 'pos_reference',
                },
                DATE: {
                    repr: (order) => moment(order.creation_date).format('YYYY-MM-DD hh:mm A'),
                    displayName: this.env._t('Date'),
                    modelField: 'date_order',
                },
                PARTNER: {
                    repr: (order) => order.get_partner_name(),
                    displayName: this.env._t('Customer'),
                    modelField: 'partner_id.display_name',
                },
            };

            if (this.showCardholderName()) {
                fields.CARDHOLDER_NAME = {
                    repr: (order) => order.get_cardholder_name(),
                    displayName: this.env._t('Cardholder Name'),
                    modelField: 'payment_ids.cardholder_name',
                };
            }

            return fields;
        }
        /**
         * Maps the order screen params to order status.
         */
        _getScreenToStatusMap() {
            return {
                ProductScreen: 'ONGOING',
                PaymentScreen: 'PAYMENT',
                ReceiptScreen: 'RECEIPT',
            };
        }
        /**
         * Override to do something before deleting the order.
         * Make sure to return true to proceed on deleting the order.
         * @param {*} order
         * @returns {boolean}
         */
        async _onBeforeDeleteOrder(order) {
            return true;
        }
        _getOrderStates() {
            // We need the items to be ordered, therefore, Map is used instead of normal object.
            const states = new Map();
            states.set('ACTIVE_ORDERS', {
                text: this.env._t('All active orders'),
            });
            // The spaces are important to make sure the following states
            // are under the category of `All active orders`.
            states.set('ONGOING', {
                text: this.env._t('Ongoing'),
                indented: true,
            });
            states.set('PAYMENT', {
                text: this.env._t('Payment'),
                indented: true,
            });
            states.set('RECEIPT', {
                text: this.env._t('Receipt'),
                indented: true,
            });
            return states;
        }
        //#region SEARCH SYNCED ORDERS
        _computeSyncedOrdersDomain() {
            const { fieldName, searchTerm } = this._state.ui.searchDetails;
            if (!searchTerm) return [];
            const modelField = this._getSearchFields()[fieldName].modelField;
            if (modelField) {
                return [[modelField, 'ilike', `%${searchTerm}%`]];
            } else {
                return [];
            }
        }
        /**
         * Fetches the done orders from the backend that needs to be shown.
         * If the order is already in cache, the full information about that
         * order is not fetched anymore, instead, we use info from cache.
         */
        async _fetchSyncedOrders() {
            const domain = this._computeSyncedOrdersDomain();
            const limit = this._state.syncedOrders.nPerPage;
            const offset = (this._state.syncedOrders.currentPage - 1) * this._state.syncedOrders.nPerPage;
            const { ids, totalCount } = await this.rpc({
                model: 'pos.order',
                method: 'search_paid_order_ids',
                kwargs: { config_id: this.env.pos.config.id, domain, limit, offset },
                context: this.env.session.user_context,
            });
            const idsNotInCache = ids.filter((id) => !(id in this._state.syncedOrders.cache));
            if (idsNotInCache.length > 0) {
                const fetchedOrders = await this.rpc({
                    model: 'pos.order',
                    method: 'export_for_ui',
                    args: [idsNotInCache],
                    context: this.env.session.user_context,
                });
                // Check for missing products and partners and load them in the PoS
                await this.env.pos._loadMissingProducts(fetchedOrders);
                await this.env.pos._loadMissingPartners(fetchedOrders);
                // Cache these fetched orders so that next time, no need to fetch
                // them again, unless invalidated. See `_onInvoiceOrder`.
                fetchedOrders.forEach((order) => {
                    this._state.syncedOrders.cache[order.id] = Order.create({}, { pos: this.env.pos, json: order });
                });
            }
            this._state.syncedOrders.totalCount = totalCount;
            this._state.syncedOrders.toShow = ids.map((id) => this._state.syncedOrders.cache[id]);
        }
        _getLastPage() {
            const totalCount = this._state.syncedOrders.totalCount;
            const nPerPage = this._state.syncedOrders.nPerPage;
            const remainder = totalCount % nPerPage;
            if (remainder == 0) {
                return totalCount / nPerPage;
            } else {
                return Math.ceil(totalCount / nPerPage);
            }
        }
        //#endregion
        //#endregion
    }
    TicketScreen.template = 'TicketScreen';
    TicketScreen.defaultProps = {
        destinationOrder: null,
        // When passed as true, it will use the saved _state.ui as default
        // value when this component is reinstantiated.
        // After setting the default value, the _state.ui will be overridden
        // by the passed props.ui if there is any.
        reuseSavedUIState: false,
        ui: {},
    };

    Registries.Component.add(TicketScreen);

    return TicketScreen;
});
