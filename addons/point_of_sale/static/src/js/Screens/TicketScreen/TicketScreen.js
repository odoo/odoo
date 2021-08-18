odoo.define('point_of_sale.TicketScreen', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');
    const { useListener, useAutofocus } = require('web.custom_hooks');
    const { posbus } = require('point_of_sale.utils');

    const makeDefaultSearchDetails = () => ({
        fieldName: 'RECEIPT_NUMBER',
        searchTerm: '',
    });
    const TICKET_SCREEN_STATE = {
        syncedOrders: {
            currentPage: 1,
            cache: {},
            toShow: [],
            nPerPage: 80,
            totalCount: null,
        },
        ui: {
            selectedSyncedOrderId: null,
            searchDetails: makeDefaultSearchDetails(),
            filter: null,
        },
    };

    class TicketScreen extends IndependentToOrderScreen {
        constructor() {
            super(...arguments);
            useListener('close-screen', this.close);
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            useListener('click-order', this._onClickOrder);
            useListener('create-new-order', this._onCreateNewOrder);
            useListener('delete-order', this._onDeleteOrder);
            useListener('next-page', this._onNextPage);
            useListener('prev-page', this._onPrevPage);
            useListener('order-invoiced', this._onInvoiceOrder);
            useAutofocus({ selector: '.search input'});
            this._state = TICKET_SCREEN_STATE;
            const defaultUIState = this.props.reuseSavedUIState
                ? this._state.ui
                : {
                      selectedSyncedOrderId: null,
                      searchDetails: makeDefaultSearchDetails(),
                      filter: null,
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
                    title: 'Existing orderlines',
                    body: `${order.name} has total amount of ${this.getTotal(
                        order
                    )}.\n Are you sure you want delete this order?`,
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
            this._invalidateSyncedOrdersCache([orderId]);
            await this._fetchSyncedOrders();
            this.render();
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
                return this._getOrderStates().get(this._getScreenToStatusMap()[screen.name]);
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
        //#endregion
        //#region PRIVATE METHODS
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
            orderStates.set('SYNCED', this.env._t('Paid'));
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
            states.set('ACTIVE_ORDERS', this.env._t('Active Orders'));
            states.set('ONGOING', this.env._t('Ongoing'));
            states.set('PAYMENT', this.env._t('Payment'));
            states.set('RECEIPT', this.env._t('Receipt'));
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
        _invalidateSyncedOrdersCache(ids) {
            for (let id of ids) {
                delete this._state.syncedOrders.cache[id];
            }
        }
        //#endregion
        //#endregion
    }
    TicketScreen.template = 'TicketScreen';
    TicketScreen.defaultProps = {
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
