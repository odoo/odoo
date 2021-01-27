odoo.define('point_of_sale.TicketScreen', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const IndependentToOrderScreen = require('point_of_sale.IndependentToOrderScreen');
    const { useListener } = require('web.custom_hooks');
    const { posbus } = require('point_of_sale.utils');

    class TicketScreen extends IndependentToOrderScreen {
        constructor() {
            super(...arguments);
            useListener('close-screen', this.close);
            useListener('filter-selected', this._onFilterSelected);
            useListener('search', this._onSearch);
            this.searchDetails = {};
            this.filter = null;
            this._initializeSearchFieldConstants();
        }
        mounted() {
            posbus.on('ticket-button-clicked', this, this.close);
            this.env.pos.get('orders').on('add remove change', () => this.render(), this);
            this.env.pos.on('change:selectedOrder', () => this.render(), this);
        }
        willUnmount() {
            posbus.off('ticket-button-clicked', this);
            this.env.pos.get('orders').off('add remove change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
        }
        _onFilterSelected(event) {
            this.filter = event.detail.filter;
            this.render();
        }
        _onSearch(event) {
            const searchDetails = event.detail;
            Object.assign(this.searchDetails, searchDetails);
            this.render();
        }
        /**
         * Override to conditionally show the new ticket button.
         */
        get showNewTicketButton() {
            return true;
        }
        get orderList() {
            return this.env.pos.get_order_list();
        }
        get filteredOrderList() {
            const { AllTickets } = this.getOrderStates();
            const filterCheck = (order) => {
                if (this.filter && this.filter !== AllTickets) {
                    const screen = order.get_screen_data();
                    return this.filter === this.constants.screenToStatusMap[screen.name];
                }
                return true;
            };
            const { fieldValue, searchTerm } = this.searchDetails;
            const fieldAccessor = this._searchFields[fieldValue];
            const searchCheck = (order) => {
                if (!fieldAccessor) return true;
                const fieldValue = fieldAccessor(order);
                if (fieldValue === null) return true;
                if (!searchTerm) return true;
                return fieldValue && fieldValue.toString().toLowerCase().includes(searchTerm.toLowerCase());
            };
            const predicate = (order) => {
                return filterCheck(order) && searchCheck(order);
            };
            return this.orderList.filter(predicate);
        }
        selectOrder(order) {
            this._setOrder(order);
            if (order === this.env.pos.get_order()) {
                this.close();
            }
        }
        _setOrder(order) {
            this.env.pos.set_order(order);
        }
        createNewOrder() {
            this.env.pos.add_new_order();
        }
        async deleteOrder(order) {
            const screen = order.get_screen_data();
            if (['ProductScreen', 'PaymentScreen'].includes(screen.name) && order.get_orderlines().length > 0) {
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: 'Existing orderlines',
                    body: `${order.name} has total amount of ${this.getTotal(
                        order
                    )}, are you sure you want delete this order?`,
                });
                if (!confirmed) return;
            }
            if (order) {
                await this._canDeleteOrder(order);
                order.destroy({ reason: 'abandon' });
            }
            posbus.trigger('order-deleted');
        }
        getDate(order) {
            return moment(order.creation_date).format('YYYY-MM-DD hh:mm A');
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
            const screen = order.get_screen_data();
            return this.constants.screenToStatusMap[screen.name];
        }
        /**
         * Hide the delete button if one of the payments is a 'done' electronic payment.
         */
        hideDeleteButton(order) {
            return order
                .get_paymentlines()
                .some((payment) => payment.is_electronic() && payment.get_payment_status() === 'done');
        }
        showCardholderName() {
            return this.env.pos.payment_methods.some(method => method.use_payment_terminal);
        }
        get searchBarConfig() {
            return {
                searchFields: this.constants.searchFieldNames,
                filter: { show: true, options: this.filterOptions },
            };
        }
        get filterOptions() {
            const { AllTickets, Ongoing, Payment, Receipt } = this.getOrderStates();
            return [AllTickets, Ongoing, Payment, Receipt];
        }
        /**
         * An object with keys containing the search field names which map to functions.
         * The mapped functions will be used to generate representative string for the order
         * to match the search term when searching.
         * E.g. Given 2 orders, search those with `Receipt Number` containing `1111`.
         * ```
         * orders = [{
         *    name: '000-1111-222'
         *    total: 10,
         *   }, {
         *    name: '444-5555-666'
         *    total: 15,
         * }]
         * ```
         * `Receipt Number` search field maps to the `name` of the order. So, the orders will be
         * represented by their name, and the search will result to:
         * ```
         * result = [{
         *    name: '000-1111-222',
         *    total: 10,
         * }]
         * ```
         * @returns Record<string, (models.Order) => string>
         */
        get _searchFields() {
            const { ReceiptNumber, Date, Customer, CardholderName } = this.getSearchFieldNames();
            var fields = {
                [ReceiptNumber]: (order) => order.name,
                [Date]: (order) => moment(order.creation_date).format('YYYY-MM-DD hh:mm A'),
                [Customer]: (order) => order.get_client_name(),
            };

            if (this.showCardholderName()) {
                fields[CardholderName] = (order) => order.get_cardholder_name();
            }

            return fields;
        }
        /**
         * Maps the order screen params to order status.
         */
        get _screenToStatusMap() {
            const { Ongoing, Payment, Receipt } = this.getOrderStates();
            return {
                ProductScreen: Ongoing,
                PaymentScreen: Payment,
                ReceiptScreen: Receipt,
            };
        }
        _initializeSearchFieldConstants() {
            this.constants = {};
            Object.assign(this.constants, {
                searchFieldNames: Object.keys(this._searchFields),
                screenToStatusMap: this._screenToStatusMap,
            });
        }
        async _canDeleteOrder(order) {
            return true;
        }
        getOrderStates() {
            return {
                AllTickets: this.env._t('All Tickets'),
                Ongoing: this.env._t('Ongoing'),
                Payment: this.env._t('Payment'),
                Receipt: this.env._t('Receipt'),
            };
        }
        getSearchFieldNames() {
            return {
                ReceiptNumber: this.env._t('Receipt Number'),
                Date: this.env._t('Date'),
                Customer: this.env._t('Customer'),
                CardholderName: this.env._t('Cardholder Name'),
            };
        }
    }
    TicketScreen.template = 'TicketScreen';

    Registries.Component.add(TicketScreen);

    return TicketScreen;
});
