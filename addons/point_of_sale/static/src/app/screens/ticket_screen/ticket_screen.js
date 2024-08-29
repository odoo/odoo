import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { parseFloat } from "@web/views/fields/parsers";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { BackButton } from "@point_of_sale/app/screens/product_screen/action_pad/back_button/back_button";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { CenteredIcon } from "@point_of_sale/app/generic_components/centered_icon/centered_icon";
import { ReprintReceiptButton } from "@point_of_sale/app/screens/ticket_screen/reprint_receipt_button/reprint_receipt_button";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component, useChildSubEnv, useState } from "@odoo/owl";
import {
    BACKSPACE,
    Numpad,
    getButtons,
    DEFAULT_LAST_ROW,
} from "@point_of_sale/app/generic_components/numpad/numpad";
import { PosOrderLineRefund } from "@point_of_sale/app/models/pos_order_line_refund";
import { View } from "@web/views/view";
import { session } from "@web/session";

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
        Numpad,
        BackButton,
        View,
    };
    static props = {
        destinationOrder: { type: [Object, { value: null }], optional: true },
        context: { type: Object, optional: true },
    };
    static defaultProps = {
        destinationOrder: null,
        context: {},
    };

    setup() {
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.numberBuffer = useService("number_buffer");
        this.numberBuffer.use({
            triggerAtInput: (event) => this._onUpdateSelectedOrderline(event),
        });
        this.session = session;
        this.state = useState({
            selectedOrder: this.pos.get_order() || null,
            selectedOrderlineIds: {},
        });
        // This sets up the "title" of the list view
        useChildSubEnv({ config: { breadcrumbs: [{ name: _t("Orders") }] } });
    }
    getNumpadButtons() {
        return getButtons(DEFAULT_LAST_ROW, [
            { value: "quantity", text: _t("Qty"), class: "active border-primary" },
            { value: "discount", text: _t("% Disc"), disabled: true },
            { value: "price", text: _t("Price"), disabled: true },
            BACKSPACE,
        ]);
    }
    // openFormView() {
    //     this.dialog.add(
    //         FormViewDialog,
    //         {
    //             resModel: "pos.order",
    //             resId: this.getSelectedOrder().id,
    //         },
    //         {
    //             onClose: () => {
    //                 // This is a workaround to refresh the list view of the orders.
    //                 // it's because from the form view the user might have created a refund order
    //                 // and we need to refresh the list view to show this new order.
    //                 this.pos.showScreen("TicketScreen", this.props);
    //             },
    //         }
    //     );
    // }
    async onClickOrder(clickedOrderId) {
        const clickedOrder = (await this.pos.data.read("pos.order", [clickedOrderId]))[0];
        this.pos.ticket_screen_mobile_pane = "right";
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

        this.postRefund(destinationOrder);

        this.closeTicketScreen();
    }

    postRefund(destinationOrder) {}

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
    get isOrderSynced() {
        return (
            this.state.selectedOrder?.uiState.locked &&
            this.state.selectedOrder.get_screen_data().name === ""
        );
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
}

registry.category("pos_screens").add("TicketScreen", TicketScreen);
