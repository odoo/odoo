odoo.define('point_of_sale.TicketScreen', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const { useListener, useAutofocus } = require('web.custom_hooks');
    const { posbus } = require('point_of_sale.utils');
    const { parse } = require('web.field_utils');


    class TicketScreen extends IndependentToOrderScreen {
        constructor() {
            super(...arguments);
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
            useAutofocus({ selector: '.search input' });
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
        }
        //#region LIFECYCLE METHODS
        mounted() {
            posbus.on('ticket-button-clicked', this, this.close);
            this.env.pos.get('orders').on('add remove change', () => this.render(), this);
            this.env.pos.on('change:selectedOrder', () => this.render(), this);
            setTimeout(() => {
                // Show updated list of synced orders when going back to the screen.
                this._onFilterSelected({ detail: { filter: this._state.ui.filter } });
            });
        }
        willUnmount() {
            posbus.off('ticket-button-clicked', this);
            this.env.pos.get('orders').off('add remove change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
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
            this.render();
        }
        async _onSearch(event) {
            Object.assign(this._state.ui.searchDetails, event.detail);
            if (this._state.ui.filter == 'SYNCED') {
                this._state.syncedOrders.currentPage = 1;
                await this._fetchSyncedOrders();
            }
            this.render();
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
            this.render();
        }
        _onCreateNewOrder() {
            this.env.pos.add_new_order();
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
                order.destroy({ reason: 'abandon' });
                posbus.trigger('order-deleted');
            }
        }
        async _onNextPage() {
            if (this._state.syncedOrders.currentPage < this._getLastPage()) {
                this._state.syncedOrders.currentPage += 1;
                await this._fetchSyncedOrders();
            }
            this.render();
        }
        async _onPrevPage() {
            if (this._state.syncedOrders.currentPage > 1) {
                this._state.syncedOrders.currentPage -= 1;
                await this._fetchSyncedOrders();
            }
            this.render();
        }
        async _onInvoiceOrder({ detail: orderId }) {
            this.env.pos._invalidateSyncedOrdersCache([orderId]);
            await this._fetchSyncedOrders();
            this.render();
        }
        _onClickOrderline({ detail: orderline }) {
            const order = this.getSelectedSyncedOrder();
            this._state.ui.selectedOrderlineIds[order.backendId] = orderline.id;
            NumberBuffer.reset();
            this.render();
        }
        _onClickRefundOrderUid({ detail: orderUid }) {
            // Open the refund order.
            const refundOrder = this.env.pos.get('orders').models.find((order) => order.uid == orderUid);
            if (refundOrder) {
                this._setOrder(refundOrder);
            }
        }
        _onUpdateSelectedOrderline({ detail }) {
            const buffer = detail.buffer;
            const order = this.getSelectedSyncedOrder();
            if (!order) return NumberBuffer.reset();

            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.models.find((line) => line.id == selectedOrderlineId);
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
            this.render();
        }
        async _onDoRefund() {
            const order = this.getSelectedSyncedOrder();
            if (!order) {
                this._state.ui.highlightHeaderNote = !this._state.ui.highlightHeaderNote;
                return this.render();
            }

            if (this._doesOrderHaveSoleItem(order)) {
                this._prepareAutoRefundOnOrder(order);
            }

            const customer = order.get_client();

            // Select the lines from toRefundLines (can come from different orders)
            // such that:
            //   - the quantity to refund is not zero
            //   - if there is customer in the selected paid order, select the items
            //     with the same orderPartnerId
            //   - it is not yet linked to an active order (no destinationOrderUid)
            const allToRefundDetails = Object.values(this.env.pos.toRefundLines).filter(
                ({ qty, orderline, destinationOrderUid }) =>
                    !this.env.pos.isProductQtyZero(qty) &&
                    (customer ? orderline.orderPartnerId == customer.id : true) &&
                    !destinationOrderUid
            );
            if (allToRefundDetails.length == 0) {
                this._state.ui.highlightHeaderNote = !this._state.ui.highlightHeaderNote;
                return this.render();
            }

            // The order that will contain the refund orderlines.
            // Use the destinationOrder from props if the order to refund has the same
            // customer as the destinationOrder.
            const destinationOrder =
                this.props.destinationOrder && customer === this.props.destinationOrder.get_client()
                    ? this.props.destinationOrder
                    : this.env.pos.add_new_order({ silent: true });

            // Add orderline for each toRefundDetail to the destinationOrder.
            for (const refundDetail of allToRefundDetails) {
                const { qty, orderline } = refundDetail;
                await destinationOrder.add_product(this.env.pos.db.get_product_by_id(orderline.productId), {
                    quantity: -qty,
                    price: orderline.price,
                    lst_price: orderline.price,
                    extras: { price_manually_set: true },
                    merge: false,
                    refunded_orderline_id: orderline.id,
                    tax_ids: orderline.tax_ids,
                    discount: orderline.discount,
                });
                refundDetail.destinationOrderUid = destinationOrder.uid;
            }

            // Set the customer to the destinationOrder.
            if (customer && !destinationOrder.get_client()) {
                destinationOrder.set_client(customer);
            }

            this._onCloseScreen();
        }
        //#endregion
        //#region PUBLIC METHODS
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
        getCustomer(order) {
            return order.get_client_name();
        }
        getCardholderName(order) {
            return order.get_cardholder_name();
        }
        getEmployee(order) {
            return order.employee ? order.employee.name : '';
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
         * Hide the delete button if one of the payments is a 'done' electronic payment.
         */
        shouldHideDeleteButton(order) {
            return (
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
        getSelectedClient() {
            const order = this.getSelectedSyncedOrder();
            return order ? order.get_client() : null;
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
        _doesOrderHaveSoleItem(order) {
            const orderlines = order.get_orderlines();
            if (orderlines.length !== 1) return false;
            const theOrderline = orderlines[0];
            const refundableQty = theOrderline.get_quantity() - theOrderline.refunded_qty;
            return this.env.pos.isProductQtyZero(refundableQty - 1);
        }
        _prepareAutoRefundOnOrder(order) {
            const selectedOrderlineId = this.getSelectedOrderlineId();
            const orderline = order.orderlines.models.find((line) => line.id == selectedOrderlineId);
            if (!orderline) return;

            const toRefundDetail = this._getToRefundDetail(orderline);
            const refundableQty = orderline.get_quantity() - orderline.refunded_qty;
            if (this.env.pos.isProductQtyZero(refundableQty - 1)) {
                toRefundDetail.qty = 1;
            }
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
                const customer = orderline.order.get_client();
                const orderPartnerId = customer ? customer.id : false;
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
        _setOrder(order) {
            this.env.pos.set_order(order);
            if (order === this.env.pos.get_order()) {
                this.close();
            }
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
                CUSTOMER: {
                    repr: (order) => order.get_client_name(),
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
                // Check for missing products and load them in the PoS
                await this.env.pos._loadMissingProducts(fetchedOrders);
                // Cache these fetched orders so that next time, no need to fetch
                // them again, unless invalidated. See `_onInvoiceOrder`.
                fetchedOrders.forEach((order) => {
                    this._state.syncedOrders.cache[order.id] = new models.Order({}, { pos: this.env.pos, json: order });
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
