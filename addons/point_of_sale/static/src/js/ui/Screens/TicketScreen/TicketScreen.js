/** @odoo-module alias=point_of_sale.TicketScreen **/

import PosComponent from 'point_of_sale.PosComponent';
import { useListener } from 'web.custom_hooks';
import SearchBar from 'point_of_sale.SearchBar';

class TicketScreen extends PosComponent {
    constructor() {
        super(...arguments);
        useListener('filter-selected', ({ detail: filter }) =>
            this.env.model.actionHandler({ name: 'actionSetTicketScreenFilter', args: [filter] })
        );
        useListener('search', ({ detail: searchDetails }) =>
            this.env.model.actionHandler({ name: 'actionSetTicketScreenSearchDetails', args: [searchDetails] })
        );
    }
    async onClickOrder(order) {
        await this.env.model.actionHandler({ name: 'actionSelectOrder', args: [order] });
    }
    async onDeleteOrder(order) {
        const orderlines = this.env.model.getOrderlines(order);
        if (['ProductScreen', 'PaymentScreen'].includes(order._extras.activeScreen) && orderlines.length > 0) {
            const message = _.str.sprintf(
                this.env._t('%s has total amount of %s, are you sure you want delete this order?'),
                this.env.model.getOrderName(order),
                this.env.model.formatCurrency(this.getTotal(order))
            );
            const confirmed = await this.env.ui.askUser('ConfirmPopup', {
                title: this.env._t('Existing orderlines'),
                body: message,
            });
            if (confirmed) {
                await this.env.model.actionHandler({ name: 'actionDeleteOrder', args: [order] });
            }
        } else {
            await this.env.model.actionHandler({ name: 'actionDeleteOrder', args: [order] });
        }
    }
    async onClickDiscard() {
        const previousScreen = this.env.model.getPreviousScreen();
        const selection = this.env.model.getOrdersSelection();
        if (!selection.length && this.env.model._shouldSetScreenToOrder(previousScreen)) {
            await this.env.model.actionHandler({ name: 'actionCreateNewOrder' });
        } else {
            await this.env.model.actionHandler({ name: 'actionToggleScreen', args: ['TicketScreen'] });
        }
    }
    /**
     * Override to conditionally show the new ticket button.
     */
    get showNewTicketButton() {
        return true;
    }
    get filteredOrderList() {
        const { AllTickets } = this.getOrderStates();
        const filter = this.env.model.data.uiState.TicketScreen.filter || '';
        const filterCheck = (order) => {
            if (filter && filter !== AllTickets) {
                const screen = this.env.model.getOrderScreen(order);
                return filter === this.screenToStatus[screen];
            }
            return true;
        };
        const { field, term } = this.env.model.data.uiState.TicketScreen.searchDetails || {
            field: undefined,
            term: undefined,
        };
        const fieldAccessor = this.searchFieldAccessors[field];
        const searchCheck = (order) => {
            if (!fieldAccessor) return true;
            const fieldValue = fieldAccessor(order);
            if (fieldValue === null) return true;
            if (!term) return true;
            return fieldValue && fieldValue.toString().toLowerCase().includes(term.toLowerCase());
        };
        const predicate = (order) => {
            return filterCheck(order) && searchCheck(order);
        };

        // IMPROVEMENT: Is it better if sorted? If so, apply this and fix the TicketScreen tour.
        // .sort((a, b) => new Date(b.date_order) - new Date(a.date_order));
        return this.getOrdersToShow(predicate);
    }
    getOrdersToShow(predicate) {
        return this.env.model.getDraftOrders().filter(predicate);
    }
    getReceiptNumber(order) {
        const orderName = this.env.model.getOrderName(order);
        const uid = orderName.match(/\d{5,}-\d{3,}-\d{4,}/);
        if (uid) return uid[0];
        return orderName;
    }
    getDate(order) {
        return moment(order.date_order).format('YYYY-MM-DD hh:mm A');
    }
    getTotal(order) {
        const { withTaxWithDiscount } = this.env.model.getOrderTotals(order);
        return withTaxWithDiscount;
    }
    getCardholderName(order) {
        const defaultName = '';
        for (const payment of this.env.model.getPayments(order)) {
            if (payment.cardholder_name) return payment.cardholder_name;
        }
        return defaultName;
    }
    getEmployee(order) {
        const user = this.env.model.getRecord('res.users', order.user_id);
        return user ? user.name : '';
    }
    getStatus(order) {
        return this.screenToStatus[this.env.model.getOrderScreen(order)];
    }
    /**
     * Hide the delete button if one of the payments is a 'done' electronic payment.
     */
    hideDeleteButton(order) {
        const payments = this.env.model.getPayments(order);
        return payments.some((payment) => payment.payment_status && payment.payment_status === 'done');
    }
    showCardholderName() {
        return this.env.model.data.derived.paymentMethods.some((method) => method.use_payment_terminal);
    }
    get searchBarConfig() {
        return {
            searchFields: Object.keys(this.searchFieldAccessors),
            filter: { show: true, options: this.filterOptions },
            initSearchTerm: this.env.model.data.uiState.TicketScreen.searchDetails.term,
            initFilter: this.env.model.data.uiState.TicketScreen.filter,
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
    get searchFieldAccessors() {
        const { ReceiptNumber, Date, Customer, CardholderName } = this.getSearchFieldNames();
        const fields = {
            [ReceiptNumber]: (order) => this.env.model.getOrderName(order),
            [Date]: (order) => moment(order.date_order).format('YYYY-MM-DD hh:mm A'),
            [Customer]: (order) => this.env.model.getCustomerName(order),
        };

        if (this.showCardholderName()) {
            fields[CardholderName] = (order) => this.getCardholderName(order);
        }

        return fields;
    }
    /**
     * Maps the order screen params to order status.
     */
    get screenToStatus() {
        const { Ongoing, Payment, Receipt } = this.getOrderStates();
        return {
            ProductScreen: Ongoing,
            PaymentScreen: Payment,
            ReceiptScreen: Receipt,
        };
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
TicketScreen.components = { SearchBar };
TicketScreen.template = 'point_of_sale.TicketScreen';

export default TicketScreen;
