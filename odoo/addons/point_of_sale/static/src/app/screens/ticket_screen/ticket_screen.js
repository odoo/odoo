/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { parseFloat } from "@web/views/fields/parsers";
import { _t } from "@web/core/l10n/translation";

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";

import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { CenteredIcon } from "@point_of_sale/app/generic_components/centered_icon/centered_icon";
import { ReprintReceiptButton } from "@point_of_sale/app/screens/ticket_screen/reprint_receipt_button/reprint_receipt_button";
import { SearchBar } from "@point_of_sale/app/screens/ticket_screen/search_bar/search_bar";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, useState } from "@odoo/owl";
import { Numpad } from "@point_of_sale/app/generic_components/numpad/numpad";

const { DateTime } = luxon;

export class TicketScreen extends Component {
    static storeOnOrder = false;
    static template = "point_of_sale.TicketScreen";
    static components = {
        ActionpadWidget,
        InvoiceButton,
        Orderline,
        OrderWidget,
        CenteredIcon,
        ReprintReceiptButton,
        SearchBar,
        Numpad,
    };
    static defaultProps = {
        destinationOrder: null,
        // When passed as true, it will use the saved _state.ui as default
        // value when this component is reinstantiated.
        // After setting the default value, the _state.ui will be overridden
        // by the passed props.ui if there is any.
        reuseSavedUIState: false,
        ui: {},
    };
    static numpadActionName = _t("Refund");
    static searchPlaceholder = _t("Search Orders...");

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtInput: (event) => this._onUpdateSelectedOrderline(event),
        });
        this._state = this.pos.TICKET_SCREEN_STATE;
        const defaultUIState = this.props.reuseSavedUIState
            ? this._state.ui
            : {
                  selectedOrder: this.pos.get_order(),
                  searchDetails: this.pos.getDefaultSearchDetails(),
                  filter: null,
                  selectedOrderlineIds: {},
              };
        Object.assign(this._state.ui, defaultUIState, this.props.ui || {});

        onMounted(this.onMounted);
    }
    //#region LIFECYCLE METHODS
    onMounted() {
        setTimeout(() => {
            // Show updated list of synced orders when going back to the screen.
            this.onFilterSelected(this._state.ui.filter);
        });
    }
    //#endregion
    //#region EVENT HANDLERS
    async onFilterSelected(selectedFilter) {
        this._state.ui.filter = selectedFilter;
        if (this._state.ui.filter == "ACTIVE_ORDERS" || this._state.ui.filter === null) {
            this._state.ui.selectedOrder = this.pos.get_order();
        }
        if (this._state.ui.filter == "SYNCED") {
            await this._fetchSyncedOrders();
        }
    }
    getNumpadButtons() {
        return [
            { value: "1" },
            { value: "2" },
            { value: "3" },
            { value: "quantity", text: _t("Qty"), class: "active border-primary" },
            { value: "4" },
            { value: "5" },
            { value: "6" },
            { value: "discount", text: _t("% Disc"), disabled: true },
            { value: "7" },
            { value: "8" },
            { value: "9" },
            { value: "price", text: _t("Price"), disabled: true },
            { value: "-", text: "+/-", disabled: true },
            { value: "0" },
            { value: this.env.services.localization.decimalPoint },
            { value: "Backspace", text: "⌫" },
        ];
    }
    async onSearch(search) {
        Object.assign(this._state.ui.searchDetails, search);
        if (this._state.ui.filter == "SYNCED") {
            this._state.syncedOrders.currentPage = 1;
            await this._fetchSyncedOrders();
        }
    }
    onClickOrder(clickedOrder) {
        this._state.ui.selectedOrder = clickedOrder;
        this.numberBuffer.reset();
        if ((!clickedOrder || clickedOrder.locked) && !this.getSelectedOrderlineId()) {
            // Automatically select the first orderline of the selected order.
            const firstLine = this._state.ui.selectedOrder.get_orderlines()[0];
            if (firstLine) {
                this._state.ui.selectedOrderlineIds[clickedOrder.backendId] = firstLine.id;
            }
        }
    }
    onCreateNewOrder() {
        this.pos.add_new_order();
        this.pos.showScreen("ProductScreen");
    }
    _selectNextOrder(currentOrder) {
        const currentOrderIndex = this._getOrderList().indexOf(currentOrder);
        const orderList = this._getOrderList();
        this.pos.set_order(orderList[currentOrderIndex + 1] || orderList[currentOrderIndex - 1]);
    }
    async onDeleteOrder(order) {
        const screen = order.get_screen_data();
        if (
            ["ProductScreen", "PaymentScreen"].includes(screen.name) &&
            order.get_orderlines().length > 0
        ) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: _t("Existing orderlines"),
                body: _t(
                    "%s has a total amount of %s, are you sure you want to delete this order?",
                    order.name,
                    this.getTotal(order)
                ),
            });
            if (!confirmed) {
                return confirmed;
            }
        }
        if (order && (await this._onBeforeDeleteOrder(order))) {
            if (Object.keys(order.lastOrderPrepaChange).length > 0) {
                await this.pos.sendOrderInPreparationUpdateLastChange(order, true);
            }
            if (order === this.pos.get_order()) {
                this._selectNextOrder(order);
            }
            this.pos.removeOrder(order);
            if (this._state.ui.selectedOrder === order) {
                if (this.pos.get_order_list().length > 0) {
                    this._state.ui.selectedOrder = this.pos.get_order_list()[0];
                } else {
                    this._state.ui.selectedOrder = null;
                }
            }
        }
        if (this.pos.isOpenOrderShareable()) {
            await this.pos._removeOrdersFromServer();
        }
        return true;
    }
    async onNextPage() {
        if (this._state.syncedOrders.currentPage < this._getLastPage()) {
            this._state.syncedOrders.currentPage += 1;
            await this._fetchSyncedOrders();
        }
    }
    async onPrevPage() {
        if (this._state.syncedOrders.currentPage > 1) {
            this._state.syncedOrders.currentPage -= 1;
            await this._fetchSyncedOrders();
        }
    }
    async onInvoiceOrder(orderId) {
        this.pos._invalidateSyncedOrdersCache([orderId]);
        await this._fetchSyncedOrders();
    }
    onClickOrderline(orderline) {
        if (this._state.ui.selectedOrder.locked) {
            const order = this.getSelectedOrder();
            this._state.ui.selectedOrderlineIds[order.backendId] = orderline.id;
            this.numberBuffer.reset();
        }
    }
    onClickRefundOrderUid(orderUid) {
        // Open the refund order.
        const refundOrder = this.pos.orders.find((order) => order.uid == orderUid);
        if (refundOrder) {
            this._setOrder(refundOrder);
        }
    }
    _onUpdateSelectedOrderline({ key, buffer }) {
        const order = this.getSelectedOrder();
        if (!order) {
            return this.numberBuffer.reset();
        }

        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
        if (!orderline) {
            return this.numberBuffer.reset();
        }

        const toRefundDetails = orderline
            .getAllLinesInCombo()
            .map((line) => this._getToRefundDetail(line));
        for (const toRefundDetail of toRefundDetails) {
            // When already linked to an order, do not modify the to refund quantity.
            if (toRefundDetail.destinationOrderUid) {
                return this.numberBuffer.reset();
            }

            const refundableQty =
                toRefundDetail.orderline.qty - toRefundDetail.orderline.refundedQty;
            if (refundableQty <= 0) {
                return this.numberBuffer.reset();
            }

            if (buffer == null || buffer == "") {
                toRefundDetail.qty = 0;
            } else {
                const quantity = Math.abs(parseFloat(buffer));
                if (quantity > refundableQty) {
                    this.numberBuffer.reset();
                    if (!toRefundDetail.orderline.comboParent) {
                        this.popup.add(ErrorPopup, {
                            title: _t("Maximum Exceeded"),
                            body: _t(
                                "The requested quantity to be refunded is higher than the ordered quantity. %s is requested while only %s can be refunded.",
                                quantity,
                                refundableQty
                            ),
                        });
                    }
                } else {
                    toRefundDetail.qty = quantity;
                }
            }
        }
    }
    async addAdditionalRefundInfo(order, destinationOrder) {
        // used by L10N, e.g: add a refund reason using a specific L10N field
        return Promise.resolve();
    }
    async onDoRefund() {
        const order = this.getSelectedOrder();

        if (order && this._doesOrderHaveSoleItem(order)) {
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

        const invoicedOrderIds = new Set(
            allToRefundDetails
                .filter(
                    (detail) =>
                        this._state.syncedOrders.cache[detail.orderline.orderBackendId]?.state ===
                        "invoiced"
                )
                .map((detail) => detail.orderline.orderBackendId)
        );

        if (invoicedOrderIds.size > 1) {
            this.popup.add(ErrorPopup, {
                title: _t("Multiple Invoiced Orders Selected"),
                body: _t(
                    "You have selected orderlines from multiple invoiced orders. To proceed refund, please select orderlines from the same invoiced order."
                ),
            });
            return;
        }

        // The order that will contain the refund orderlines.
        // Use the destinationOrder from props if the order to refund has the same
        // partner as the destinationOrder.
        const destinationOrder =
            this.props.destinationOrder &&
            partner === this.props.destinationOrder.get_partner() &&
            !this.pos.doNotAllowRefundAndSales()
                ? this.props.destinationOrder
                : this._getEmptyOrder(partner);

        // Add orderline for each toRefundDetail to the destinationOrder.
        const originalToDestinationLineMap = new Map();

        // First pass: add all products to the destination order
        for (const refundDetail of allToRefundDetails) {
            const product = this.pos.db.get_product_by_id(refundDetail.orderline.productId);
            const options = this._prepareRefundOrderlineOptions(refundDetail);
            const newOrderline = await destinationOrder.add_product(product, options);
            originalToDestinationLineMap.set(refundDetail.orderline.id, newOrderline);
            refundDetail.destinationOrderUid = destinationOrder.uid;
        }
        // Second pass: update combo relationships in the destination order
        for (const refundDetail of allToRefundDetails) {
            const originalOrderline = refundDetail.orderline;
            const destinationOrderline = originalToDestinationLineMap.get(originalOrderline.id);
            if (originalOrderline.comboParent) {
                const comboParentLine = originalToDestinationLineMap.get(
                    originalOrderline.comboParent.id
                );
                if (comboParentLine) {
                    destinationOrderline.comboParent = comboParentLine;
                }
            }
            if (originalOrderline.comboLines && originalOrderline.comboLines.length > 0) {
                destinationOrderline.comboLines = originalOrderline.comboLines.map((comboLine) => {
                    return originalToDestinationLineMap.get(comboLine.id);
                });
            }
        }
        //Add a check too see if the fiscal position exist in the pos
        if (order.fiscal_position_not_found) {
            this.showPopup("ErrorPopup", {
                title: _t("Fiscal Position not found"),
                body: _t(
                    "The fiscal position used in the original order is not loaded. Make sure it is loaded by adding it in the pos configuration."
                ),
            });
            return;
        }
        destinationOrder.fiscal_position = order.fiscal_position;
        // Set the partner to the destinationOrder.
        this.setPartnerToRefundOrder(partner, destinationOrder);

        if (this.pos.get_order().cid !== destinationOrder.cid) {
            this.pos.set_order(destinationOrder);
        }
        await this.addAdditionalRefundInfo(order, destinationOrder);

        this.closeTicketScreen();
    }
    setPartnerToRefundOrder(partner, destinationOrder) {
        if (partner && !destinationOrder.get_partner()) {
            destinationOrder.set_partner(partner);
        }
    }
    //#endregion
    //#region PUBLIC METHODS
    getSelectedOrder() {
        if (this._state.ui.filter == "SYNCED" && this._state.ui.selectedOrder) {
            return this._state.syncedOrders.cache[this._state.ui.selectedOrder.backendId];
        } else {
            return this._state.ui.selectedOrder;
        }
    }
    getSelectedOrderlineId() {
        if (this._state.ui.selectedOrder?.backendId) {
            return this._state.ui.selectedOrderlineIds[this._state.ui.selectedOrder.backendId];
        }
    }
    /**
     * Override to conditionally show the new order button, or prevent order
     * creation when leaving the screen.
     *
     * @returns {boolean}
     */
    get allowNewOrders() {
        return true;
    }
    get isOrderSynced() {
        return this._state.ui.selectedOrder?.locked;
    }
    getFilteredOrderList() {
        if (this._state.ui.filter == "SYNCED") {
            return this._state.syncedOrders.toShow;
        }
        const filterCheck = (order) => {
            if (this._state.ui.filter && this._state.ui.filter !== "ACTIVE_ORDERS") {
                const screen = order.get_screen_data();
                return this._state.ui.filter === this._getScreenToStatusMap()[screen.name];
            }
            return true;
        };
        const { fieldName, searchTerm } = this._state.ui.searchDetails;
        const searchField = this._getSearchFields()[fieldName];
        const searchCheck = (order) => {
            if (!searchField) {
                return true;
            }
            const repr = searchField.repr(order);
            if (repr === null) {
                return true;
            }
            if (!searchTerm) {
                return true;
            }
            return repr && repr.toString().toLowerCase().includes(searchTerm.toLowerCase());
        };
        const predicate = (order) => {
            return filterCheck(order) && searchCheck(order);
        };
        return this._getOrderList().filter(predicate);
    }
    getDate(order) {
        return formatDateTime(order.date_order);
    }
    getTotal(order) {
        return this.env.utils.formatCurrency(order.get_total_with_tax());
    }
    getPartner(order) {
        return order.get_partner_name();
    }
    getCardholderName(order) {
        return order.get_cardholder_name();
    }
    getCashier(order) {
        return order.cashier ? order.cashier.name : "";
    }
    getStatus(order) {
        if (order.locked) {
            return order.state === "invoiced" ? _t("Invoiced") : _t("Paid");
        } else {
            const screen = order.get_screen_data();
            return this._getOrderStates().get(this._getScreenToStatusMap()[screen.name]).text;
        }
    }
    /**
     * If the order is the only order and is empty
     */
    isDefaultOrderEmpty(order) {
        const status = this._getScreenToStatusMap()[order.get_screen_data().name];
        const productScreenStatus = this._getScreenToStatusMap().ProductScreen;
        return (
            order.get_orderlines().length === 0 &&
            this.pos.get_order_list().length === 1 &&
            status === productScreenStatus &&
            order.get_paymentlines().length === 0
        );
    }
    /**
     * Hide the delete button if one of the payments is a 'done' electronic payment.
     */
    shouldHideDeleteButton(order) {
        return (
            (this.ui.isSmall && order != this._state.ui.selectedOrder) ||
            this.isDefaultOrderEmpty(order) ||
            order.locked ||
            order
                .get_paymentlines()
                .some(
                    (payment) => payment.is_electronic() && payment.get_payment_status() === "done"
                )
        );
    }
    isHighlighted(order) {
        const selectedOrder = this.getSelectedOrder();

        return selectedOrder
            ? (order.backendId && order.backendId == selectedOrder.backendId) ||
                  order.uid === selectedOrder.uid
            : false;
    }
    showCardholderName() {
        return this.pos.payment_methods.some((method) => method.use_payment_terminal);
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
        return this._state.ui.filter == "SYNCED" && this._getLastPage() > 1;
    }
    getPageNumber() {
        if (!this._state.syncedOrders.totalCount) {
            return `1/1`;
        } else {
            return `${this._state.syncedOrders.currentPage}/${this._getLastPage()}`;
        }
    }
    getSelectedPartner() {
        const order = this.getSelectedOrder();
        return order ? order.get_partner() : null;
    }
    getHasItemsToRefund() {
        const order = this.getSelectedOrder();
        if (!order) {
            return false;
        }
        if (this._doesOrderHaveSoleItem(order)) {
            return true;
        }
        const total = Object.values(this.pos.toRefundLines)
            .filter(
                (toRefundDetail) =>
                    toRefundDetail.orderline.orderUid === order.uid &&
                    !toRefundDetail.destinationOrderUid
            )
            .map((toRefundDetail) => toRefundDetail.qty)
            .reduce((acc, val) => acc + val, 0);
        return !this.pos.isProductQtyZero(total);
    }
    switchPane() {
        this.pos.switchPaneTicketScreen();
    }
    closeTicketScreen() {
        this.pos.ticket_screen_mobile_pane = "left";
        this.pos.closeScreen();
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
        for (const order of this.pos.orders) {
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
        return emptyOrderForPartner || emptyOrder || this.pos.add_new_order();
    }
    _doesOrderHaveSoleItem(order) {
        const orderlines = order.get_orderlines();
        if (orderlines.length !== 1) {
            return false;
        }
        const theOrderline = orderlines[0];
        const refundableQty = theOrderline.get_quantity() - theOrderline.refunded_qty;
        return this.pos.isProductQtyZero(refundableQty - 1);
    }
    _prepareAutoRefundOnOrder(order) {
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = order.orderlines.find((line) => line.id == selectedOrderlineId);
        if (!orderline) {
            return false;
        }

        const toRefundDetail = this._getToRefundDetail(orderline);
        const refundableQty = orderline.get_quantity() - orderline.refunded_qty;
        if (this.pos.isProductQtyZero(refundableQty - 1) && toRefundDetail.qty === 0) {
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
        const { toRefundLines } = this.pos;
        if (orderline.id in toRefundLines) {
            return toRefundLines[orderline.id];
        }
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
                tax_ids: orderline.get_taxes().map((tax) => tax.id),
                discount: orderline.discount,
                pack_lot_lines: orderline.pack_lot_lines
                    ? orderline.pack_lot_lines.map((lot) => {
                          return { lot_name: lot.lot_name };
                      })
                    : false,
                comboParent: orderline.comboParent,
                comboLines: orderline.comboLines,
            },
            destinationOrderUid: false,
        };
        toRefundLines[orderline.id] = newToRefundDetail;
        return newToRefundDetail;
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
        return Object.values(this.pos.toRefundLines).filter(
            ({ qty, orderline, destinationOrderUid }) =>
                !this.pos.isProductQtyZero(qty) &&
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
        const draftPackLotLines = orderline.pack_lot_lines
            ? { modifiedPackLotLines: [], newPackLotLines: orderline.pack_lot_lines }
            : false;
        return {
            quantity: -qty,
            price: orderline.price,
            extras: { price_type: "automatic" },
            merge: false,
            refunded_orderline_id: orderline.id,
            tax_ids: orderline.tax_ids,
            discount: orderline.discount,
            draftPackLotLines: draftPackLotLines,
        };
    }
    _setOrder(order) {
        if (this.pos.isOpenOrderShareable()) {
            this.pos.sendDraftToServer();
        }
        this.pos.set_order(order);
        this.closeTicketScreen();
    }
    _getOrderList() {
        return this.pos.get_order_list();
    }
    _getFilterOptions() {
        const orderStates = this._getOrderStates();
        orderStates.set("SYNCED", { text: _t("Paid") });
        return orderStates;
    }
    /**
     * @returns {Record<string, { repr: (order: models.Order) => string, displayName: string, modelField: string }>}
     */
    _getSearchFields() {
        const fields = {
            TRACKING_NUMBER: {
                repr: (order) => order.trackingNumber,
                displayName: _t("Order Number"),
                modelField: "tracking_number",
            },
            RECEIPT_NUMBER: {
                repr: (order) => order.name,
                displayName: _t("Receipt Number"),
                modelField: "pos_reference",
            },
            DATE: {
                repr: (order) => formatDateTime(order.date_order),
                displayName: _t("Date"),
                modelField: "date_order",
                formatSearch: (searchTerm) => {
                    const includesTime = searchTerm.includes(':');
                    let parsedDateTime;
                    try {
                        parsedDateTime = parseDateTime(searchTerm);
                    } catch {
                        return searchTerm;
                    }
                    if (includesTime) {
                        return parsedDateTime.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
                    } else {
                        return parsedDateTime.toFormat("yyyy-MM-dd");
                    }
                }
            },
            PARTNER: {
                repr: (order) => order.get_partner_name(),
                displayName: _t("Customer"),
                modelField: "partner_id.complete_name",
            },
        };

        if (this.showCardholderName()) {
            fields.CARDHOLDER_NAME = {
                repr: (order) => order.get_cardholder_name(),
                displayName: _t("Cardholder Name"),
                modelField: "payment_ids.cardholder_name",
            };
        }

        return fields;
    }
    /**
     * Maps the order screen params to order status.
     */
    _getScreenToStatusMap() {
        return {
            ProductScreen: "ONGOING",
            PaymentScreen: "PAYMENT",
            ReceiptScreen: "RECEIPT",
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
        states.set("ACTIVE_ORDERS", {
            text: _t("All active orders"),
        });
        // The spaces are important to make sure the following states
        // are under the category of `All active orders`.
        states.set("ONGOING", {
            text: _t("Ongoing"),
            indented: true,
        });
        states.set("PAYMENT", {
            text: _t("Payment"),
            indented: true,
        });
        states.set("RECEIPT", {
            text: _t("Receipt"),
            indented: true,
        });
        return states;
    }
    //#region SEARCH SYNCED ORDERS
    _computeSyncedOrdersDomain() {
        let { fieldName, searchTerm } = this._state.ui.searchDetails;
        if (!searchTerm) {
            return [];
        }
        const searchField = this._getSearchFields()[fieldName];
        if (searchField) {
            if (searchField.formatSearch) {
                searchTerm = searchField.formatSearch(searchTerm);
            }
            return [[searchField.modelField, "ilike", `%${searchTerm}%`]];
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
        const offset =
            (this._state.syncedOrders.currentPage - 1) * this._state.syncedOrders.nPerPage;
        const config_id = this.pos.config.id;
        let { ordersInfo, totalCount } = await this.orm.call(
            "pos.order",
            "search_paid_order_ids",
            [],
            { config_id, domain, limit, offset }
        );
        const idsNotInCache = ordersInfo.filter(
            (orderInfo) => !(orderInfo[0] in this._state.syncedOrders.cache)
        );
        // If no cacheDate, then assume reasonable earlier date.
        const cacheDate = this._state.syncedOrders.cacheDate || DateTime.fromMillis(0);
        const idsNotUpToDate = ordersInfo.filter((orderInfo) => {
            return deserializeDateTime(orderInfo[1]) > cacheDate;
        });
        const idsToLoad = idsNotInCache.concat(idsNotUpToDate).map((info) => info[0]);
        if (idsToLoad.length > 0) {
            const fetchedOrders = await this.orm.call("pos.order", "export_for_ui", [idsToLoad]);
            // Remove not loaded Order IDs
            const fetchedOrderIds = new Set(fetchedOrders.map(order => order.id));
            const notLoadedIds = idsNotInCache.filter((orderInfo) => !fetchedOrderIds.has(orderInfo[0]));
            ordersInfo = ordersInfo.filter((orderInfo) => !notLoadedIds.includes(orderInfo[0]));
            // Check for missing products and partners and load them in the PoS
            await this.pos._loadMissingProducts(fetchedOrders);
            await this.pos._loadMissingPartners(fetchedOrders);
            // Cache these fetched orders so that next time, no need to fetch
            // them again, unless invalidated. See `_onInvoiceOrder`.
            fetchedOrders.forEach((order) => {
                this._state.syncedOrders.cache[order.id] = new Order(
                    { env: this.env },
                    { pos: this.pos, json: order }
                );
            });
            //Update the datetime indicator of the cache refresh
            this._state.syncedOrders.cacheDate = DateTime.local();
        }

        const ids = ordersInfo.map((info) => info[0]);
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

registry.category("pos_screens").add("TicketScreen", TicketScreen);
