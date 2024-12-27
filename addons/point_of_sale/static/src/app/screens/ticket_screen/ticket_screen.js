import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { parseFloat } from "@web/views/fields/parsers";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { CenteredIcon } from "@point_of_sale/app/generic_components/centered_icon/centered_icon";
import { ReprintReceiptButton } from "@point_of_sale/app/screens/ticket_screen/reprint_receipt_button/reprint_receipt_button";
import { SearchBar } from "@point_of_sale/app/screens/ticket_screen/search_bar/search_bar";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, onMounted, onWillStart, useState } from "@odoo/owl";
import {
    BACKSPACE,
    Numpad,
    getButtons,
    DEFAULT_LAST_ROW,
} from "@point_of_sale/app/generic_components/numpad/numpad";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";
import { PosOrderLineRefund } from "@point_of_sale/app/models/pos_order_line_refund";
import { fuzzyLookup } from "@web/core/utils/search";
import { parseUTCString } from "@point_of_sale/utils";

const NBR_BY_PAGE = 30;

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
    static props = {
        destinationOrder: { type: Object, optional: true },
        reuseSavedUIState: { type: Boolean, optional: true },
        stateOverride: { type: Object, optional: true },
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
        this.dialog = useService("dialog");
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtInput: (event) => this._onUpdateSelectedOrderline(event),
        });

        this.state = useState({
            page: 1,
            nbrPage: 1,
            filter: null,
            search: this.pos.getDefaultSearchDetails(),
            selectedOrder: this.pos.get_order() || null,
            selectedOrderlineIds: {},
        });
        Object.assign(this.state, this.props.stateOverride || {});

        onMounted(this.onMounted);
        onWillStart(async () => {
            if (this.pos._shouldLoadOrders()) {
                try {
                    this.pos.setLoadingOrderState(true);
                    await this.pos.getServerOrders();
                } finally {
                    this.pos.setLoadingOrderState(false);
                }
            }
        });
    }
    onMounted() {
        setTimeout(() => {
            // Show updated list of synced orders when going back to the screen.
            this.onFilterSelected(this.state.filter);
        });
    }
    async onFilterSelected(selectedFilter) {
        this.state.filter = selectedFilter;

        if (this.state.filter == "SYNCED") {
            await this._fetchSyncedOrders();
        }
    }
    getNumpadButtons() {
        return getButtons(DEFAULT_LAST_ROW, [
            { value: "quantity", text: _t("Qty"), class: "active border-primary" },
            { value: "discount", text: _t("% Disc"), disabled: true },
            { value: "price", text: _t("Price"), disabled: true },
            BACKSPACE,
        ]);
    }
    async onSearch(search) {
        this.state.search = search;
        this.state.page = 1;
        if (this.state.filter == "SYNCED") {
            await this._fetchSyncedOrders();
        }
    }
    onClickOrder(clickedOrder) {
        this.state.selectedOrder = clickedOrder;
        this.numberBuffer.reset();
        if ((!clickedOrder || clickedOrder.uiState.locked) && !this.getSelectedOrderlineId()) {
            // Automatically select the first orderline of the selected order.
            const firstLine = this.state.selectedOrder.get_orderlines()[0];
            if (firstLine) {
                this.state.selectedOrderlineIds[clickedOrder.id] = firstLine.id;
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
            const confirmed = await ask(this.dialog, {
                title: _t("Existing orderlines"),
                body: _t(
                    "%s has a total amount of %s, are you sure you want to delete this order?",
                    order.name,
                    this.getTotal(order)
                ),
            });
            if (!confirmed) {
                return false;
            }
            if (this.state.selectedOrder?.id === order.id) {
                this.state.selectedOrder = null;
            }
        }

        order.uiState.displayed = false;
        if (order.id === this.pos.get_order()?.id) {
            this._selectNextOrder(order);
        }

        const result = await this.pos.deleteOrders([order]);
        if (!result) {
            order.uiState.displayed = true;
        } else {
            if (this.pos.get_open_orders().length > 0) {
                this.state.selectedOrder = this.pos.get_open_orders()[0];
            }
        }

        return true;
    }
    async onNextPage() {
        if (this.state.page < this.getNbrPages()) {
            this.state.page += 1;
            await this._fetchSyncedOrders();
        }
    }
    async onPrevPage() {
        if (this.state.page > 1) {
            this.state.page -= 1;
            await this._fetchSyncedOrders();
        }
    }
    async onInvoiceOrder(orderId) {
        const order = this.pos.models["pos.order"].get(orderId);
        this.state.selectedOrder = order;
    }
    onClickOrderline(orderline) {
        if (this.state.selectedOrder.uiState.locked) {
            const order = this.getSelectedOrder();
            this.state.selectedOrderlineIds[order.id] = orderline.id;
            this.numberBuffer.reset();
        }
    }
    onClickRefundOrderUid(orderUuid) {
        // Open the refund order.
        const refundOrder = this.pos.models["pos.order"].find((order) => order.uuid == orderUuid);
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
        const orderline = order.lines.find((line) => line.id == selectedOrderlineId);
        if (!orderline) {
            return this.numberBuffer.reset();
        }

        const toRefundDetails = orderline
            .getAllLinesInCombo()
            .map((line) => this.getToRefundDetail(line));
        for (const toRefundDetail of toRefundDetails) {
            // When already linked to an order, do not modify the to refund quantity.
            if (toRefundDetail.destionation_order_id) {
                return this.numberBuffer.reset();
            }

            const refundableQty = toRefundDetail.line.qty - toRefundDetail.line.refunded_qty;
            if (refundableQty <= 0) {
                return this.numberBuffer.reset();
            }

            if (buffer == null || buffer == "") {
                toRefundDetail.qty = 0;
            } else {
                const quantity = Math.abs(parseFloat(buffer));
                if (quantity > refundableQty) {
                    this.numberBuffer.reset();
                    if (!toRefundDetail.line.combo_parent_id) {
                        this.dialog.add(AlertDialog, {
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

        if (!order || !this.getHasItemsToRefund()) {
            return;
        }

        const partner = order.get_partner();
        // The order that will contain the refund orderlines.
        // Use the destinationOrder from props if the order to refund has the same
        // partner as the destinationOrder.
        const destinationOrder =
            this.props.destinationOrder &&
            this.props.destinationOrder.lines.every(
                (l) =>
                    l.quantity >= 0 || order.lines.some((ol) => ol.id === l.refunded_orderline_id)
            ) &&
            partner === this.props.destinationOrder.get_partner() &&
            !this.pos.doNotAllowRefundAndSales()
                ? this.props.destinationOrder
                : this._getEmptyOrder(partner);

        destinationOrder.takeaway = order.takeaway;
        // Add orderline for each toRefundDetail to the destinationOrder.
        const lines = [];
        for (const refundDetail of this._getRefundableDetails(partner, order)) {
            const refundLine = refundDetail.line;
            const line = this.pos.models["pos.order.line"].create({
                qty: -refundDetail.qty,
                price_unit: refundLine.price_unit,
                product_id: refundLine.product_id,
                order_id: destinationOrder,
                discount: refundLine.discount,
                tax_ids: refundLine.tax_ids.map((tax) => ["link", tax]),
                refunded_orderline_id: refundLine,
                pack_lot_ids: refundLine.pack_lot_ids.map((packLot) => ["link", packLot]),
                price_type: "automatic",
            });
            lines.push(line);
            refundDetail.destination_order_uuid = destinationOrder.uuid;
        }
        // link the refund combo lines
        const refundComboParentLines = lines.filter(
            (l) => l.refunded_orderline_id.combo_line_ids.length > 0
        );
        for (const refundComboParent of refundComboParentLines) {
            const children = refundComboParent.refunded_orderline_id.combo_line_ids
                .map((l) => l.refund_orderline_ids)
                .flat();
            refundComboParent.update({
                combo_line_ids: [["link", ...children]],
            });
        }

        //Add a check too see if the fiscal position exist in the pos
        if (order.fiscal_position_not_found) {
            this.dialog.add(AlertDialog, {
                title: _t("Fiscal Position not found"),
                body: _t(
                    "The fiscal position used in the original order is not loaded. Make sure it is loaded by adding it in the pos configuration."
                ),
            });
            return;
        }

        if (order.fiscal_position_id) {
            destinationOrder.update({ fiscal_position_id: order.fiscal_position_id });
        }
        // Set the partner to the destinationOrder.
        this.setPartnerToRefundOrder(partner, destinationOrder);

        if (this.pos.get_order().uuid !== destinationOrder.uuid) {
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
    getSelectedOrder() {
        return this.state.selectedOrder;
    }
    getSelectedOrderlineId() {
        if (this.state.selectedOrder) {
            return this.state.selectedOrderlineIds[this.state.selectedOrder.id];
        }
    }
    get allowNewOrders() {
        return true;
    }
    get isOrderSynced() {
        return (
            this.state.selectedOrder?.uiState.locked &&
            (this.state.selectedOrder.get_screen_data().name === "" ||
                this.state.filter === "SYNCED")
        );
    }
    activeOrderFilter(o) {
        const screen = ["ReceiptScreen", "TipScreen"];
        const oScreen = o.get_screen_data();
        return (!o.finalized || screen.includes(oScreen.name)) && o.uiState.displayed;
    }
    getFilteredOrderList() {
        const orderModel = this.pos.models["pos.order"];
        let orders =
            this.state.filter === "SYNCED"
                ? orderModel.filter((o) => o.finalized && o.uiState.displayed)
                : orderModel.filter(this.activeOrderFilter);

        if (this.state.filter && !["ACTIVE_ORDERS", "SYNCED"].includes(this.state.filter)) {
            orders = orders.filter((order) => {
                const screen = order.get_screen_data();
                return this._getScreenToStatusMap()[screen.name] === this.state.filter;
            });
        }

        if (this.state.search.searchTerm) {
            const repr = this._getSearchFields()[this.state.search.fieldName].repr;
            orders = fuzzyLookup(this.state.search.searchTerm, orders, repr);
        }

        const sortOrders = (orders, ascending = false) =>
            orders.sort((a, b) => {
                const dateA = parseUTCString(a.date_order, "yyyy-MM-dd HH:mm:ss");
                const dateB = parseUTCString(b.date_order, "yyyy-MM-dd HH:mm:ss");

                if (a.date_order !== b.date_order) {
                    return ascending ? dateA - dateB : dateB - dateA;
                } else {
                    const nameA = parseInt(a.name.replace(/\D/g, "")) || 0;
                    const nameB = parseInt(b.name.replace(/\D/g, "")) || 0;
                    return ascending ? nameA - nameB : nameB - nameA;
                }
            });

        if (this.state.filter === "SYNCED") {
            return sortOrders(orders).slice(
                (this.state.page - 1) * NBR_BY_PAGE,
                this.state.page * NBR_BY_PAGE
            );
        } else {
            return sortOrders(orders, true);
        }
    }
    getDate(order) {
        return formatDateTime(parseUTCString(order.date_order));
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
        return order.employee_id ? order.employee_id.name : "";
    }
    getStatus(order) {
        if (
            order.uiState?.locked &&
            (order.get_screen_data().name === "" || this.state.filter === "SYNCED")
        ) {
            return _t("Paid");
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
            this.pos.get_open_orders().length === 1 &&
            status === productScreenStatus &&
            order.payment_ids.length === 0
        );
    }
    /**
     * Hide the delete button if one of the payments is a 'done' electronic payment.
     */
    shouldHideDeleteButton(order) {
        return (
            (this.ui.isSmall && order != this.state.selectedOrder) ||
            this.isDefaultOrderEmpty(order) ||
            order.finalized ||
            order.payment_ids.some(
                (payment) => payment.is_electronic() && payment.get_payment_status() === "done"
            )
        );
    }
    isHighlighted(order) {
        const selectedOrder = this.getSelectedOrder();
        return selectedOrder ? order.id && order.id == selectedOrder.id : false;
    }
    showCardholderName() {
        return this.pos.models["pos.payment.method"].some((method) => method.use_payment_terminal);
    }
    getSearchBarConfig() {
        return {
            searchFields: new Map(
                Object.entries(this._getSearchFields()).map(([key, val]) => [key, val.displayName])
            ),
            filter: { show: true, options: this._getFilterOptions() },
            defaultSearchDetails: this.state.search,
            defaultFilter: this.state.filter,
        };
    }
    getNbrPages() {
        return Math.ceil(this.pos.ticketScreenState.totalCount / NBR_BY_PAGE);
    }
    getPageNumber() {
        if (!this.pos.ticketScreenState.totalCount) {
            return `1/1`;
        } else {
            return `${this.state.page}/${this.getNbrPages()}`;
        }
    }
    getHasItemsToRefund() {
        const order = this.getSelectedOrder();
        if (!order) {
            return false;
        }
        if (this._doesOrderHaveSoleItem(order)) {
            return true;
        }
        const total = Object.values(order.uiState.lineToRefund).reduce((acc, val) => {
            acc += val.qty;
            return acc;
        }, 0);

        return !this.pos.isProductQtyZero(total);
    }
    switchPane() {
        this.pos.switchPaneTicketScreen();
    }
    closeTicketScreen() {
        this.pos.ticket_screen_mobile_pane = "left";
        this.pos.closeScreen();
    }
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
        for (const order of this.pos.models["pos.order"].filter((order) => !order.finalized)) {
            if (order.get_orderlines().length === 0 && order.payment_ids.length === 0) {
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
        const orderline = order.lines.find((line) => line.id == selectedOrderlineId);
        if (!orderline) {
            return false;
        }

        const toRefundDetail = this.getToRefundDetail(orderline);
        if (this.pos.isProductQtyZero(toRefundDetail.maxQty - 1) && toRefundDetail.qty === 0) {
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
    getToRefundDetail(orderline) {
        const lineToRefund = orderline.order_id.uiState.lineToRefund;

        if (orderline.uuid in lineToRefund) {
            return lineToRefund[orderline.uuid];
        }

        const newToRefundDetail = new PosOrderLineRefund(
            {
                line_uuid: orderline.uuid,
                qty: 0,
            },
            this.pos.models
        );

        lineToRefund[orderline.uuid] = newToRefundDetail;
        return newToRefundDetail;
    }
    /**
     * Select the lines from lineToRefund, as they can come from different orders.
     * Returns only details that:
     * - The quantity to refund is not zero
     * - Filtered by partner (optional)
     * - It's not yet linked to an active order (no destinationOrderUid)
     *
     * @param {Object} partner (optional)
     * @param {Order} order
     * @returns {Array} refundableDetails
     */
    _getRefundableDetails(partner, order) {
        return Object.values(this.pos.linesToRefund).filter(
            (refund) =>
                !this.pos.isProductQtyZero(refund.qty) &&
                refund.line.order_id.uuid === order.uuid &&
                (partner ? refund.line.order_id.partner_id?.id === partner.id : true) &&
                !refund.destination_order_id
        );
    }

    async _setOrder(order) {
        if (this.pos.isOpenOrderShareable()) {
            await this.pos.syncAllOrders();
        }
        this.pos.set_order(order);
        this.closeTicketScreen();
    }
    _getOrderList() {
        return this.pos.models["pos.order"].getAll();
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
                repr: (order) => order.tracking_number,
                displayName: _t("Order Number"),
                modelField: "tracking_number",
            },
            RECEIPT_NUMBER: {
                repr: (order) => order.pos_reference,
                displayName: _t("Receipt Number"),
                modelField: "pos_reference",
            },
            DATE: {
                repr: (order) => this.getDate(order),
                displayName: _t("Date"),
                modelField: "date_order",
                formatSearch: (searchTerm) => {
                    const includesTime = searchTerm.includes(":");
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
                },
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
        let { fieldName, searchTerm } = this.state.search;
        if (!searchTerm) {
            return [];
        }
        const searchField = this._getSearchFields()[fieldName];
        if (searchField && searchField.modelField && searchField.modelField !== null) {
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
        const screenState = this.pos.ticketScreenState;
        const domain = this._computeSyncedOrdersDomain();
        const offset = screenState.offsetByDomain[JSON.stringify(domain)] || 0;
        const config_id = this.pos.config.id;
        const { ordersInfo, totalCount } = await this.pos.data.call(
            "pos.order",
            "search_paid_order_ids",
            [],
            {
                config_id,
                domain,
                limit: 30,
                offset,
            }
        );

        if (!screenState.offsetByDomain[JSON.stringify(domain)]) {
            screenState.offsetByDomain[JSON.stringify(domain)] = 0;
        }
        screenState.offsetByDomain[JSON.stringify(domain)] += ordersInfo.length;
        screenState.totalCount = totalCount;

        const idsNotInCacheOrOutdated = ordersInfo
            .filter((orderInfo) => {
                const order = this.pos.models["pos.order"].get(orderInfo[0]);

                if (order && parseUTCString(orderInfo[1]) > parseUTCString(order.date_order)) {
                    return true;
                }

                return !order;
            })
            .map((info) => info[0]);

        if (idsNotInCacheOrOutdated.length > 0) {
            await this.pos.data.read("pos.order", Array.from(new Set(idsNotInCacheOrOutdated)));
        }
    }
}

registry.category("pos_screens").add("TicketScreen", TicketScreen);
