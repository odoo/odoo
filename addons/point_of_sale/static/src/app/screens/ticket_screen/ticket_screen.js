import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    formatDate,
    parseDate,
    parseDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { parseFloat } from "@web/views/fields/parsers";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { BackButton } from "@point_of_sale/app/screens/product_screen/action_pad/back_button/back_button";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { PosNumberBufferPlugin } from "@point_of_sale/app/plugins/pos_number_buffer_plugin";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { CenteredIcon } from "@point_of_sale/app/components/centered_icon/centered_icon";
import { SearchBar } from "@point_of_sale/app/screens/ticket_screen/search_bar/search_bar";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    useOnChange,
    useProps,
    proxy,
    t,
    providePlugins,
    usePlugin,
} from "@odoo/owl";
import {
    BACKSPACE,
    Numpad,
    getButtons,
    ZERO,
    DECIMAL,
} from "@point_of_sale/app/components/numpad/numpad";
import { PosOrderLineRefund } from "@point_of_sale/app/models/pos_order_line_refund";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { BarcodeVideoScanner } from "@web/core/barcode/barcode_video_scanner";
import { makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { NumberPopup } from "@point_of_sale/app/components/popups/number_popup/number_popup";
import { ConnectionLostError } from "@web/core/network/rpc";
import { TipCell } from "@point_of_sale/app/screens/ticket_screen/tip_cell/tip_cell";
import { ProgressBar } from "@point_of_sale/app/screens/ticket_screen/progress_bar/progress_bar";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";
import { PrintPopup } from "@point_of_sale/app/components/popups/print_popup/print_popup";
import { OrderDetailsDialog } from "./order_details_dialog/order_details_dialog";
import { TicketOrderFilters } from "./ticket_order_filters";
import { TicketOrderList } from "./ticket_order_list";

const { DateTime } = luxon;
const NBR_BY_PAGE = 30;

export const ticketScreenProps = {
    // When passed as true, it will use the saved _state.ui as default
    // value when this component is reinstantiated.
    // After setting the default value, the _state.ui will be overridden
    // by the passed props.ui if there is any.
    reuseSavedUIState: t.boolean().optional(false),
    stateOverride: t.object().optional(),
    ui: t.object().optional({}),
};

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
        BarcodeVideoScanner,
        TipCell,
        ProgressBar,
        Dropdown,
        DropdownItem,
    };
    props = useProps(ticketScreenProps);

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.numberBuffer = usePlugin(PosNumberBufferPlugin);
        this.doPrint = useTrackedAsync((_selectedSyncedOrder) => this.print(_selectedSyncedOrder));
        this.numberBuffer.use({
            triggerAtInput: (event) => this._onUpdateSelectedOrderline(event),
            useWithBarcode: true,
        });

        this.state = proxy({
            nbrByPage: NBR_BY_PAGE,
            page: 1,
            nbrPage: 1,
            filter: null,
            search: this.pos.getDefaultSearchDetails(),
            selectedOrderUuid: this.pos.getOrder()?.uuid || null,
            selectedOrderlineIds: {},
            selectedPreset: null,
            serverPageIds: [],
            serverTotalCount: 0,
            pageSource: "server", // "local" when offline: the synced orders in memory
            loadingOrders: false,
            loadingPage: false,
        });
        this.orderTimers = proxy({});

        providePlugins([TicketOrderFilters, TicketOrderList], {
            pos: this.pos,
            state: this.state,
            getSearchFields: () => this._getSearchFields(),
        });
        this.filters = usePlugin(TicketOrderFilters);
        this.list = usePlugin(TicketOrderList);

        // --- Initialization
        onMounted(() => {
            this._timersInterval = setInterval(this.updateOrderTimers.bind(this), 60_000);
        });

        onWillStart(() => {
            this.state.loadingOrders = true;
            // Start fetching orders without blocking screen rendering
            this.pos
                .getServerOrders()
                .catch((error) => {
                    if (error instanceof ConnectionLostError) {
                        return;
                    }
                    throw error;
                })
                .finally(() => {
                    this.state.loadingOrders = false;
                    this.list.refresh(); // with the orders `getServerOrders` sent
                });
        });

        // --- Reactivity
        useOnChange(
            () => this.stateProps,
            () => {
                this.applyStateOverride(this.props.stateOverride);
            }
        );
        useOnChange(
            () => [this.list.orders()],
            () => this.updateOrderTimers()
        );

        // --- Cleanup
        onWillUnmount(() => clearInterval(this._timersInterval));
    }

    /** Props setting the state: when one changes, the state is set and the orders reloaded. */
    get stateProps() {
        return [this.props.stateOverride];
    }
    /** Sets the state given by the props, then reloads the orders (keeps the status if none). */
    async applyStateOverride(stateOverride = {}, filterOptions = {}) {
        const { filter = this.state.filter, ...others } = stateOverride;
        Object.assign(this.state, others);
        await this.setFilter(filter, filterOptions);
    }
    clearOrderTimers() {
        for (const key in this.orderTimers) {
            delete this.orderTimers[key];
        }
    }
    updateOrderTimers() {
        this.clearOrderTimers();
        for (const order of this.list.orders()) {
            if (order.preset_time) {
                if (order.preset_time > DateTime.now()) {
                    this.orderTimers[order.uuid] = Math.ceil(
                        order.preset_time.diff(DateTime.now(), "minutes").minutes
                    );
                } else {
                    this.orderTimers[order.uuid] = 0;
                }
            }
        }
    }
    async onClickPageNbr() {
        const nbr = await makeAwaitable(this.dialog, NumberPopup, {
            title: _t("Number by page"),
            isValid: (value) => value > 0 && value <= 100,
        });

        if (nbr && !isNaN(nbr)) {
            this.state.nbrByPage = Math.max(parseInt(nbr), 1);
            await this.list.reload();
        }
    }
    async onPresetSelected(preset) {
        this.state.selectedPreset = this.state.selectedPreset === preset ? null : preset;
        await this.list.reload();
        if (this.state.selectedPreset) {
            const firstFilteredOrder = this.list.orders()[0];
            if (firstFilteredOrder) {
                this.onClickOrder(firstFilteredOrder);
            }
        }
    }
    async print(order) {
        this.dialog.add(PrintPopup, { order });
    }
    onClickSend() {
        if (this.pos.canSendReceipt) {
            this.dialog.add(SendReceiptPopup, {
                order: this.getSelectedOrder(),
            });
        }
    }
    async setFilter(filter, { focusOrderId = false } = {}) {
        this.state.filter = filter;
        await this.list.reload({ focusOrderId });
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
    async onClickScanOrder(qrcode) {
        if (qrcode) {
            const uuid = new URL(qrcode).searchParams.get("order_uuid");
            const orders = await this.pos.data.loadServerOrders([["uuid", "=", uuid]]);
            const order = orders[0];
            if (order) {
                this.pos.scanning = !this.pos.scanning;
                await this.selectScannedOrder(order);
            } else {
                this.env.services.notification.add(_t("Invalid QR Code! Please, Scan again!"), {
                    type: "warning",
                });
            }
        } else {
            this.env.services.notification.add(_t("Please, Scan again!"), {
                type: "warning",
            });
        }
    }
    async selectScannedOrder(order) {
        this.setSelectedOrder(order);
        this.filters.clear();
        if (this.filters.matchesStatus(order, "ACTIVE_ORDERS")) {
            if (
                this.list.isServerPaginated ||
                !this.filters.matchesStatus(order, this.state.filter)
            ) {
                await this.setFilter("ACTIVE_ORDERS");
            }
            const index = this.list.localOrders().indexOf(order);
            if (index !== -1) {
                this.state.page = Math.floor(index / this.state.nbrByPage) + 1;
            }
            return;
        }
        const status = order.isCancelled ? "CANCELLED" : "SYNCED";
        await this.setFilter(status, { focusOrderId: order.isSynced && order.id });
    }
    async onSearch(search) {
        this.state.search = search;
        await this.list.reload();
    }
    onClickOrder(clickedOrder) {
        // Pending keystrokes belong to the line they were typed for.
        this.numberBuffer.capture();
        this.setSelectedOrder(clickedOrder);
        this.numberBuffer.reset();
        if ((!clickedOrder || clickedOrder.finalized) && !this.getSelectedOrderlineId()) {
            // Automatically select the first refundable orderline of the selected order.
            const firstLine = this.getSelectedOrder()
                .getOrderlines()
                .find((line) => line.isValidForRefund);
            if (firstLine) {
                this.state.selectedOrderlineIds[clickedOrder.id] = firstLine.id;
            }
        }
    }
    onDblClickOrder(order) {
        if (!order.finalized) {
            this.setOrder(order);
        }
    }

    _onInfoOrder(order) {
        this.dialog.add(OrderDetailsDialog, {
            order,
            editPayment: () => {
                this.dialog.closeAll();
                this.pos.editPayment(order);
            },
        });
    }
    async onClickReprintAll(order) {
        await this.pos.ticketPrinter.reprintOrderChanges({ order });
    }
    async onNextPage() {
        if (this.list.currentPage < this.list.nbrPages) {
            await this.list.changePage(this.list.currentPage + 1);
        }
    }
    async onPrevPage() {
        if (this.list.currentPage > 1) {
            await this.list.changePage(this.list.currentPage - 1);
        }
    }
    async onInvoiceOrder(orderId) {
        const order = this.pos.models["pos.order"].get(orderId);
        this.setSelectedOrder(order);
    }
    onClickOrderline(orderline) {
        if (!this.pos.accessRight.canClickOrderLine) {
            return;
        }
        const order = this.getSelectedOrder();
        if (this.isOrderSynced) {
            // A refund line (one that already refunds another line) must not
            // be refunded again, so a refund order cannot itself be refunded.
            const refundableLine = orderline.combo_parent_id || orderline;
            if (refundableLine.refunded_orderline_id) {
                return;
            }
            if (this.state.selectedOrderlineIds[order.id] == orderline.id) {
                const toRefundDetail = this.getToRefundDetail(orderline);
                if (Object.values(toRefundDetail).some((detail) => detail.destination_order_uuid)) {
                    return;
                }
                if (toRefundDetail.qty >= toRefundDetail.refundableQty) {
                    toRefundDetail.qty = 0;
                } else {
                    toRefundDetail.qty += 1;
                }
                this._onUpdateSelectedOrderline({
                    key: undefined,
                    buffer: `${toRefundDetail.qty}`,
                });
                return;
            }
            this.numberBuffer.capture();
            this.state.selectedOrderlineIds[order.id] = orderline.id;
            this.numberBuffer.reset();
        }
    }
    _setToRefundDetail(toRefundDetail, buffer) {
        // When already linked to an order, do not modify the to refund quantity.
        if (toRefundDetail.destionation_order_id) {
            return this.numberBuffer.reset();
        }

        if (toRefundDetail.refundableQty <= 0) {
            return this.numberBuffer.reset();
        }

        if (buffer == null || buffer == "") {
            toRefundDetail.qty = 0;
        } else {
            const quantity = Math.abs(parseFloat(buffer));
            if (quantity > toRefundDetail.refundableQty) {
                this.numberBuffer.reset();
                if (!toRefundDetail.line.combo_parent_id) {
                    this.dialog.add(AlertDialog, {
                        title: _t("Maximum Exceeded"),
                        body: _t(
                            "The requested quantity to be refunded is higher than the ordered quantity. %s is requested while only %s can be refunded.",
                            quantity,
                            toRefundDetail.refundableQty
                        ),
                    });
                }
            } else {
                toRefundDetail.qty = quantity;
            }
        }
    }
    _onUpdateSelectedOrderline({ key, buffer }) {
        const order = this.getSelectedOrder();
        if (!order) {
            return this.numberBuffer.reset();
        }

        const selectedOrderlineId = this.getSelectedOrderlineId();
        let orderline = order.lines.find((line) => line.id == selectedOrderlineId);
        if (!orderline) {
            return this.numberBuffer.reset();
        }

        if (orderline.combo_parent_id) {
            orderline = orderline.combo_parent_id;
        }

        const parentToRefundDetail = this.getToRefundDetail(orderline);
        this._setToRefundDetail(parentToRefundDetail, buffer);

        for (const comboLine of orderline.combo_line_ids) {
            const toRefundDetail = this.getToRefundDetail(comboLine);
            toRefundDetail.qty = (comboLine.qty / orderline.qty) * parentToRefundDetail.qty;
        }

        if (parentToRefundDetail.qty === parentToRefundDetail.refundableQty) {
            this._selectNextOrderline(order, selectedOrderlineId);
        }
    }
    _selectNextOrderline(order, selectedOrderlineId) {
        const orderlines = order.getOrderlines();
        const currentIndex = orderlines.findIndex((line) => line.id === selectedOrderlineId);
        if (currentIndex !== -1) {
            const nextLine = orderlines
                .slice(currentIndex + 1)
                .find((line) => line.isValidForRefund);
            if (nextLine) {
                this.state.selectedOrderlineIds[order.id] = nextLine.id;
                this.numberBuffer.reset();
            }
        }
    }
    async addAdditionalRefundInfo(order, destinationOrder) {
        // used by L10N, e.g: add a refund reason using a specific L10N field
        return Promise.resolve();
    }
    async onClickRefund() {
        // Flush pending keystrokes so the refund uses the quantities shown on screen.
        this.numberBuffer.capture();
        await this.onDoRefund();
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
        // We select the order if it is empty, else we create a new one.
        const destinationOrder = this._getEmptyOrder(partner);

        destinationOrder.is_refund = true;
        destinationOrder.pricelist_id = order.pricelist_id;
        // Add orderline for each toRefundDetail to the destinationOrder.
        const lines = [];
        for (const refundDetail of this._getRefundableDetails(partner, order)) {
            const line = this.pos.models["pos.order.line"].create(
                this.getRefundLinesDetails(refundDetail, destinationOrder)
            );
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

        // A refund is taxed like the order it refunds, even when that order has no fiscal position.
        destinationOrder.fiscal_position_id = order.fiscal_position_id || false;
        // Set the partner to the destinationOrder.
        this.setPartnerToRefundOrder(partner, destinationOrder);
        destinationOrder.refunded_order_id = order;
        this.pos.setOrder(destinationOrder);
        await this.addAdditionalRefundInfo(order, destinationOrder);

        this.postRefund(destinationOrder);
        this.pos.ticket_screen_mobile_pane = "left";
        destinationOrder.setScreenData({ name: "PaymentScreen" });
        this.pos.navigate("PaymentScreen", { orderUuid: destinationOrder.uuid });
    }

    getRefundLinesDetails(refundDetail, destinationOrder) {
        const refundLine = refundDetail.line;
        return {
            qty: -refundDetail.qty,
            price_unit: refundLine.price_unit,
            product_id: refundLine.product_id,
            order_id: destinationOrder,
            discount: refundLine.discount,
            tax_ids: refundLine.tax_ids.map((tax) => ["link", tax]),
            refunded_orderline_id: refundLine,
            price_type: "automatic",
            attribute_value_ids: refundLine.attribute_value_ids.map((attr) => ["link", attr]),
        };
    }

    async onDeleteOrder(order) {
        await this.pos.onDeleteOrder(order);
        this.setSelectedOrder(this.pos.getOrder());
    }

    postRefund(destinationOrder) {}

    setPartnerToRefundOrder(partner, destinationOrder) {
        if (partner && !destinationOrder.getPartner()) {
            destinationOrder.setPartner(partner);
        }
    }
    setSelectedOrder(order) {
        this.state.selectedOrderUuid = order?.uuid || null;
    }
    getSelectedOrder() {
        return this.pos.models["pos.order"].getBy("uuid", this.state.selectedOrderUuid) || null;
    }
    getSelectedOrderlineId() {
        if (this.getSelectedOrder()) {
            return this.state.selectedOrderlineIds[this.getSelectedOrder().id];
        }
    }
    get isOrderSynced() {
        const order = this.getSelectedOrder();
        return (
            order?.isPaid && (order.getScreenData().name === "" || this.state.filter === "SYNCED")
        );
    }

    get showSubPads() {
        return this.isOrderSynced && this.pos.accessRight.canShowPads;
    }

    // Used to override inside `l10n_cl_edi_pos`
    get showInvoiceButton() {
        return this.isOrderSynced;
    }

    get presetFilterButtons() {
        return this.pos.models["pos.preset"].getAll();
    }

    get buttonClasses() {
        return this.getHasItemsToRefund() ? "btn-primary" : "btn-secondary disabled";
    }
    getDate(order) {
        return this.pos.getDate(order.date_order);
    }
    getTotal(order) {
        return this.pos.formatCurrency(order.priceIncl);
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
        if (order.isCancelled) {
            return _t("Cancelled");
        }
        if (order.isPaid && (order.getScreenData().name === "" || this.state.filter === "SYNCED")) {
            return _t("Paid");
        }
        const screen = order.getScreenData();
        return this._getOrderStates().get(this.filters.getScreenToStatusMap()[screen.name])?.text;
    }
    getStatusDecoration(status) {
        if (status === "Ongoing" || status === "Payment") {
            return "info";
        }
        if (status === "Receipt" || status === "Paid") {
            return "success";
        }
        if (status === "Cancelled") {
            return "danger";
        }
        return "secondary";
    }
    /**
     * If the order is the only order and is empty
     */
    isDefaultOrderEmpty(order) {
        const status = this.filters.getScreenToStatusMap()[order.getScreenData().name];
        const productScreenStatus = this.filters.getScreenToStatusMap().ProductScreen;
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
            (this.ui.isSmall && order != this.getSelectedOrder()) ||
            this.isDefaultOrderEmpty(order) ||
            order.finalized ||
            order.payment_ids.some(
                (payment) => payment.isElectronic() && payment.getPaymentStatus() === "done"
            )
        );
    }
    isHighlighted(order) {
        const selectedOrder = this.getSelectedOrder();
        return selectedOrder ? order.id && order.id == selectedOrder.id : false;
    }
    showCardholderName() {
        return this.pos.models["pos.payment.method"].some((method) => method.useTerminal);
    }
    getSearchBarConfig() {
        return {
            searchFields: new Map(
                Object.entries(this._getSearchFields()).map(([key, val]) => [key, val.displayName])
            ),
            filter: { show: true, options: this._getOrderStates() },
            defaultSearchDetails: this.state.search,
            defaultFilter: this.state.filter,
        };
    }
    getHasItemsToRefund() {
        const order = this.getSelectedOrder();
        if (!order) {
            return false;
        }
        if (this._doesOrderHaveSoleItem(order)) {
            return true;
        }
        // A just-typed quantity may still be waiting on useWithBarcode's delay: don't grey
        // out the action while it is, or a quick click right after typing would land on a
        // disabled button instead of reaching onClickRefund's own capture().
        if (this.numberBuffer.hasPendingInput()) {
            return true;
        }
        const total = Object.values(order.uiState.lineToRefund).reduce((acc, val) => {
            if (!val.destination_order_uuid) {
                acc += val.qty;
            }
            return acc;
        }, 0);

        return !this.pos.isProductQtyZero(total);
    }
    switchPane() {
        this.pos.switchPaneTicketScreen();
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
        for (const order of this.pos.models["pos.order"].filter(
            (order) => !order.finalized && !this.pos.syncingOrders.has(order.uuid)
        )) {
            if (order.isEmptyOrder()) {
                if (order.getPartner() === partner) {
                    emptyOrderForPartner = order;
                    break;
                } else if (!order.getPartner() && emptyOrder === null) {
                    // If emptyOrderForPartner is not found, we will use the first empty order.
                    emptyOrder = order;
                }
            }
        }
        return (
            emptyOrderForPartner ||
            emptyOrder ||
            this.pos.addNewOrder({ partner_id: partner, is_refund: true })
        );
    }
    _doesOrderHaveSoleItem(order) {
        const orderlines = order.getOrderlines();
        if (orderlines.length !== 1) {
            return false;
        }
        const theOrderline = orderlines[0];
        const refundableQty = theOrderline.getQuantity() - theOrderline.refundedQty;
        return this.pos.isProductQtyZero(refundableQty - 1);
    }
    _prepareAutoRefundOnOrder(order) {
        const selectedOrderlineId = this.getSelectedOrderlineId();
        const orderline = order.lines.find((line) => line.id == selectedOrderlineId);
        if (!orderline) {
            return false;
        }

        const toRefundDetail = this.getToRefundDetail(orderline);
        if (
            this.pos.isProductQtyZero(toRefundDetail.refundableQty - 1) &&
            toRefundDetail.qty === 0
        ) {
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
                !refund.destinationOrder
        );
    }

    async setOrder(order) {
        if (this.pos.isOrderSyncing(order)) {
            return;
        }
        if (this.pos.config.isShareable) {
            await this.pos.syncAllOrders();
        }
        this.pos.setOrder(order);
        this.pos.navigateToOrderScreen(order);
    }

    onClickNewOrder() {
        const order = this.pos.createNewOrder({
            preset_id: this.state.selectedPreset || null,
        });
        this.pos.selectedOrderUuid = order.uuid;
        this.pos.addPendingOrder([order.id]);
        this.pos.navigateToOrderScreen(order);
    }

    /**
     * `repr` (browser) and `modelFields` (server) must match the same orders.
     * @returns {Record<string, { repr: (order: models.Order) => string | string[], displayName: string, modelFields: Array }>}
     */
    _getSearchFields() {
        const fields = {
            REFERENCE: {
                repr: (order) => [order.getName(), order.tracking_number],
                displayName: _t("Reference"),
                modelFields: ["tracking_number", "floating_order_name"],
            },
            RECEIPT_NUMBER: {
                repr: (order) => order.pos_reference,
                displayName: _t("Receipt Number"),
                modelFields: ["pos_reference"],
            },
            INVOICE_NUMBER: {
                repr: (order) => order.invoiceName,
                displayName: _t("Invoice Number"),
                modelFields: ["account_move.name"],
            },
            DATE: {
                // Today's orders show "Today" but also match their date, as on the server.
                repr: (order) => [this.getDate(order), formatDate(order.date_order)],
                displayName: _t("Date"),
                modelFields: ["date_order"],
                formatSearch: (searchTerm) => {
                    // A part of "Today" matches today's orders, as in the browser.
                    if (_t("Today").toLowerCase().includes(searchTerm.toLowerCase())) {
                        return serializeDate(DateTime.now());
                    }
                    const includesTime = searchTerm.includes(":");
                    try {
                        if (includesTime) {
                            return serializeDateTime(parseDateTime(searchTerm));
                        } else {
                            return serializeDate(parseDate(searchTerm));
                        }
                    } catch {
                        return searchTerm;
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
    _getOrderStates() {
        // We need the items to be ordered, therefore, Map is used instead of normal object.
        const states = new Map();
        states.set("ACTIVE_ORDERS", { text: _t("Active") });
        // `indented`: shown under `Active`.
        states.set("ONGOING", { text: _t("Ongoing"), indented: true });
        if (this.pos.config.set_tip_after_payment) {
            states.set("OPEN", { text: _t("Open"), indented: true });
            states.set("TIPPING", { text: _t("Tipping"), indented: true });
        } else {
            states.set("PAYMENT", { text: _t("Payment"), indented: true });
        }
        states.set("CANCELLED", { text: _t("Cancelled") });
        states.set("SYNCED", { text: _t("Paid") });
        return states;
    }
    getPresetTimeColor(order) {
        const slot = order.preset_id.currentSlot;
        const presetTime = order.preset_time;
        if (!slot) {
            if (presetTime < DateTime.now()) {
                return "text-bg-danger";
            } else {
                return "text-bg-light text-emphasis";
            }
        }
        if (
            slot.datetime <= presetTime &&
            presetTime < slot.datetime.plus({ minutes: order.preset_id.interval_time })
        ) {
            return "text-bg-warning";
        } else if (presetTime < slot.datetime) {
            return "text-bg-danger";
        } else {
            return "text-bg-light text-emphasis";
        }
    }

    async settleTips() {
        const promises = [];
        for (const order of this.list.orders()) {
            const amount = this.pos.parseValidFloat(order.uiState.TipScreen.inputTipAmount);

            if (!order.isSynced) {
                logPosMessage(
                    "TicketScreen",
                    "settleTips",
                    `${order.name} is not yet sync. Sync it to server before setting a tip.`
                );
                continue;
            }

            order.state = "draft";
            this.pos.selectedOrderUuid = order.uuid;
            await this.pos.setTip(amount);
            order.state = "paid";
            order.uiState.screen_data.value = { name: "", props: {} };

            const serializedTipLine = order.getSelectedOrderline().serializeForORM();
            order.getSelectedOrderline().delete();
            delete serializedTipLine["record_dependencies"];
            delete serializedTipLine["relations_uuid_mapping"];

            promises.push(
                new Promise((resolve) => {
                    const fn = async () => {
                        const tipLine = await this.pos.data.create("pos.order.line", [
                            serializedTipLine,
                        ]);
                        const state = await this.pos.data.ormWrite("pos.order", [order.id], {
                            is_tipped: true,
                            tip_amount: tipLine[0].price_unit,
                        });

                        if (state) {
                            order.update({
                                is_tipped: true,
                                tip_amount: tipLine[0].price_unit,
                            });
                        }
                        resolve();
                    };
                    fn();
                })
            );
        }

        await Promise.all(promises);
    }

    getCurrentTimePreset(order) {
        return this.orderTimers[order.uuid] ?? 0;
    }

    getMaxTimePreset(order) {
        return order.preset_id?.interval_time;
    }
}

registry.category("pos_pages").add("TicketScreen", {
    name: "TicketScreen",
    component: TicketScreen,
    route: `/pos/ui/${odoo.pos_config_id}/ticket`,
    params: {},
});
