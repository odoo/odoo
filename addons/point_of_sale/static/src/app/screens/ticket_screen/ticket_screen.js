import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { parseFloat } from "@web/views/fields/parsers";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { BackButton } from "@point_of_sale/app/screens/product_screen/action_pad/back_button/back_button";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { CenteredIcon } from "@point_of_sale/app/components/centered_icon/centered_icon";
import { SearchBar } from "@point_of_sale/app/screens/ticket_screen/search_bar/search_bar";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component, onMounted, useState } from "@odoo/owl";
import {
    BACKSPACE,
    Numpad,
    getButtons,
    ZERO,
    DECIMAL,
} from "@point_of_sale/app/components/numpad/numpad";
import { PosOrderLineRefund } from "@point_of_sale/app/models/pos_order_line_refund";
import { fuzzyLookup } from "@web/core/utils/search";
import { parseUTCString } from "@point_of_sale/utils";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";

const NBR_BY_PAGE = 30;

export class TicketScreen extends Component {
    static storeOnOrder = false;
    static template = "point_of_sale.TicketScreen";
    static components = {
        ActionpadWidget,
        InvoiceButton,
        Orderline,
        OrderDisplay,
        CenteredIcon,
        SearchBar,
        Numpad,
        BackButton,
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

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.numberBuffer = useService("number_buffer");
        this.doPrint = useTrackedAsync((_selectedSyncedOrder) =>
            this.pos.printReceipt({ order: _selectedSyncedOrder })
        );
        this.numberBuffer.use({
            triggerAtInput: (event) => this._onUpdateSelectedOrderline(event),
        });

        this.state = useState({
            page: 1,
            nbrPage: 1,
            filter: null,
            search: this.pos.getDefaultSearchDetails(),
            selectedOrder: this.pos.getOrder() || null,
            selectedOrderlineIds: {},
            selectedPreset: null,
        });
        Object.assign(this.state, this.props.stateOverride || {});

        onMounted(this.onMounted);
    }
    onMounted() {
        setTimeout(() => {
            // Show updated list of synced orders when going back to the screen.
            this.onFilterSelected(this.state.filter);
        });
    }
    onPresetSelected(preset) {
        if (this.state.selectedPreset === preset) {
            this.state.selectedPreset = null;
        } else {
            this.state.selectedPreset = preset;
            const firstFilteredOrder = this.getFilteredOrderList()[0];

            if (firstFilteredOrder) {
                this.onClickOrder(firstFilteredOrder);
            }
        }
    }
    async onFilterSelected(selectedFilter) {
        this.state.filter = selectedFilter;
        this.pos.ticketScreenState.totalCount = 0;
        this.pos.ticketScreenState.offsetByDomain = {};

        if (this.state.filter == "SYNCED") {
            await this._fetchSyncedOrders();
        }
    }
    getNumpadButtons() {
        return getButtons(
            [{ value: "-", text: "+/-", disabled: true }, ZERO, DECIMAL],
            [
                { value: "quantity", text: _t("Qty"), class: "active border-primary" },
                { value: "discount", text: _t("% Disc"), disabled: true },
                { value: "price", text: _t("Price"), disabled: true },
                BACKSPACE,
            ]
        );
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
            const firstLine = this.state.selectedOrder.getOrderlines()[0];
            if (firstLine) {
                this.state.selectedOrderlineIds[clickedOrder.id] = firstLine.id;
            }
        }
    }
    async onNextPage() {
        if (this.state.page < this.getNbrPages()) {
            this.state.page += 1;
            if (this.state.filter == "SYNCED") {
                await this._fetchSyncedOrders();
            }
        }
    }
    async onPrevPage() {
        if (this.state.page > 1) {
            this.state.page -= 1;
            if (this.state.filter == "SYNCED") {
                await this._fetchSyncedOrders();
            }
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

        const partner = order.getPartner();
        // The order that will contain the refund orderlines.
        // Use the destinationOrder from props if the order to refund has the same
        // partner as the destinationOrder.
        const destinationOrder =
            this.props.destinationOrder &&
            this.props.destinationOrder.lines.every(
                (l) =>
                    l.quantity >= 0 || order.lines.some((ol) => ol.id === l.refunded_orderline_id)
            ) &&
            partner === this.props.destinationOrder.getPartner() &&
            !this.pos.doNotAllowRefundAndSales()
                ? this.props.destinationOrder
                : this._getEmptyOrder(partner);

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
            refundComboParent.combo_line_ids = [["link", ...children]];
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
            destinationOrder.fiscal_position_id = order.fiscal_position_id;
        }
        // Set the partner to the destinationOrder.
        this.setPartnerToRefundOrder(partner, destinationOrder);

        if (this.pos.getOrder().uuid !== destinationOrder.uuid) {
            this.pos.setOrder(destinationOrder);
        }
        await this.addAdditionalRefundInfo(order, destinationOrder);

        this.postRefund(destinationOrder);

        this.closeTicketScreen();
    }

    postRefund(destinationOrder) {}

    setPartnerToRefundOrder(partner, destinationOrder) {
        if (partner && !destinationOrder.getPartner()) {
            destinationOrder.setPartner(partner);
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
    get isOrderSynced() {
        return (
            this.state.selectedOrder?.uiState.locked &&
            (this.state.selectedOrder.getScreenData().name === "" || this.state.filter === "SYNCED")
        );
    }
    activeOrderFilter(o) {
        const screen = ["PaymentScreen", "ProductScreen", "ReceiptScreen", "TipScreen"];
        const oScreen = o.getScreenData();
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
                const screen = order.getScreenData();
                return this._getScreenToStatusMap()[screen.name] === this.state.filter;
            });
        }

        if (this.state.search.searchTerm) {
            const repr = this._getSearchFields()[this.state.search.fieldName].repr;
            orders = fuzzyLookup(this.state.search.searchTerm, orders, repr);
        }

        if (this.state.selectedPreset) {
            orders = orders.filter((order) => order.preset_id?.id === this.state.selectedPreset.id);
        }

        const sortOrders = (orders, ascending = false) =>
            orders.sort((a, b) => {
                const dateA = parseUTCString(a.date_order, "yyyy-MM-dd HH:mm:ss");
                const dateB = parseUTCString(b.date_order, "yyyy-MM-dd HH:mm:ss");

                if (a.date_order !== b.date_order) {
                    return ascending ? dateA - dateB : dateB - dateA;
                } else {
                    const nameA = parseInt(a.pos_reference.replace(/\D/g, "")) || 0;
                    const nameB = parseInt(b.pos_reference.replace(/\D/g, "")) || 0;
                    return ascending ? nameA - nameB : nameB - nameA;
                }
            });

        if (this.state.filter === "SYNCED") {
            return sortOrders(orders).slice(
                (this.state.page - 1) * NBR_BY_PAGE,
                this.state.page * NBR_BY_PAGE
            );
        } else {
            this.pos.ticketScreenState.totalCount = orders.length;
            return sortOrders(orders, true).slice(
                (this.state.page - 1) * NBR_BY_PAGE,
                this.state.page * NBR_BY_PAGE
            );
        }
    }
    getDate(order) {
        return formatDateTime(parseUTCString(order.date_order));
    }
    getTotal(order) {
        return this.env.utils.formatCurrency(order.getTotalWithTax());
    }
    getPartner(order) {
        return order.getPartnerName();
    }
    getCardholderName(order) {
        return order.getCardHolderName();
    }
    getCashier(order) {
        return order.employee_id ? order.employee_id.name : "";
    }
    getStatus(order) {
        if (
            order.uiState?.locked &&
            (order.getScreenData().name === "" || this.state.filter === "SYNCED")
        ) {
            return _t("Paid");
        } else {
            const screen = order.getScreenData();
            return this._getOrderStates().get(this._getScreenToStatusMap()[screen.name])?.text;
        }
    }
    /**
     * If the order is the only order and is empty
     */
    isDefaultOrderEmpty(order) {
        const status = this._getScreenToStatusMap()[order.getScreenData().name];
        const productScreenStatus = this._getScreenToStatusMap().ProductScreen;
        return (
            order.getOrderlines().length === 0 &&
            this.pos.getOpenOrders().length === 1 &&
            status === productScreenStatus &&
            order.payment_ids.length === 0
        );
    }
    /**
     * Hide the delete button if one of the payments is a 'done' electronic payment.
     */
    shouldHideDeleteButton(order) {
        const orders = this.pos.models["pos.order"].filter((o) => !o.finalized);
        return (
            (orders.length === 1 && orders[0].lines.length === 0) ||
            (this.ui.isSmall && order != this.state.selectedOrder) ||
            this.isDefaultOrderEmpty(order) ||
            order.finalized ||
            order.payment_ids.some(
                (payment) => payment.isElectronic() && payment.getPaymentStatus() === "done"
            ) ||
            order.finalized
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
            return `0/0`;
        } else {
            return `${(this.state.page - 1) * NBR_BY_PAGE + 1}-${Math.min(
                this.state.page * NBR_BY_PAGE,
                this.pos.ticketScreenState.totalCount
            )} / ${this.pos.ticketScreenState.totalCount}`;
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
            if (order.getOrderlines().length === 0 && order.payment_ids.length === 0) {
                if (order.getPartner() === partner) {
                    emptyOrderForPartner = order;
                    break;
                } else if (!order.getPartner() && emptyOrder === null) {
                    // If emptyOrderForPartner is not found, we will use the first empty order.
                    emptyOrder = order;
                }
            }
        }
        return emptyOrderForPartner || emptyOrder || this.pos.addNewOrder();
    }
    _doesOrderHaveSoleItem(order) {
        const orderlines = order.getOrderlines();
        if (orderlines.length !== 1) {
            return false;
        }
        const theOrderline = orderlines[0];
        const refundableQty = theOrderline.getQuantity() - theOrderline.refunded_qty;
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
        if (this.pos.config.isShareable) {
            await this.pos.syncAllOrders();
        }
        this.pos.setOrder(order);
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
     * @returns {Record<string, { repr: (order: models.Order) => string, displayName: string, modelFields: Array }>}
     */
    _getSearchFields() {
        const fields = {
            REFERENCE: {
                repr: (order) => order.getName(),
                displayName: _t("Reference"),
                modelFields: ["tracking_number", "floating_order_name"],
            },
            RECEIPT_NUMBER: {
                repr: (order) => order.pos_reference,
                displayName: _t("Receipt Number"),
                modelFields: ["pos_reference"],
            },
            DATE: {
                repr: (order) => this.getDate(order),
                displayName: _t("Date"),
                modelFields: ["date_order"],
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
                repr: (order) => order.getPartnerName(),
                displayName: _t("Customer"),
                modelFields: ["partner_id.complete_name"],
            },
        };

        if (this.showCardholderName()) {
            fields.CARDHOLDER_NAME = {
                repr: (order) => order.getCardHolderName(),
                displayName: _t("Cardholder Name"),
                modelFields: ["payment_ids.cardholder_name"],
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
        if (searchField && searchField.modelFields && searchField.modelFields.length > 0) {
            if (searchField.formatSearch) {
                searchTerm = searchField.formatSearch(searchTerm);
            }
            const domain = [];
            for (const modelField of searchField.modelFields) {
                domain.unshift([modelField, "ilike", `%${searchTerm}%`]);
                if (domain.length > 1) {
                    domain.unshift("|");
                }
            }
            return domain;
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
