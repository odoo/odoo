import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { orderInfoPopup } from "@pos_urban_piper/point_of_sale_overrirde/app/order_info_popup/order_info_popup";

patch(TicketScreen, {
    props: {
        ...TicketScreen.props,
        upState: { optional: true },
    },
    defaultProps: {
        ...TicketScreen.defaultProps,
        upState: "",
    },
});

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.order_status = {
            placed: "Placed",
            acknowledged: "Acknowledged",
            food_ready: "Food Ready",
            dispatched: "Dispatched",
            completed: "Completed",
            cancelled: "Cancelled",
        };
        this.state.upState = this.props.upState;
    },

    /**
     * @override
     * Add two search fields.
     */
    _getSearchFields() {
        return Object.assign({}, super._getSearchFields(...arguments), {
            DELIVERYPROVIDER: {
                repr: (order) => order.get_delivery_provider_name(),
                displayName: _t("Delivery Channel"),
                modelField: "delivery_provider_id.name",
            },
            ORDERSTATUS: {
                repr: (order) => order.get_order_status(),
                displayName: _t("Delivery Order Status"),
                modelField: "delivery_status",
            },
        });
    },

    async _handleResponse(response, order, new_status) {
        const { is_success, message } = response;
        if (!is_success) {
            this.pos.notification.add(message, { type: "warning", sticky: false });
            return false;
        }
        order.delivery_status = new_status;
        return true;
    },

    async _updateScreenState(order, filterState, upState = "") {
        this.state.upState = upState;
        await this.onSearch({
            fieldName: "DELIVERYPROVIDER",
            searchTerm: order?.delivery_provider_id?.name,
        });
        await this.onFilterSelected(filterState);
    },

    async _updateOrderStatus(order, status, code = null) {
        const response = await this.pos.data.call("pos.config", "order_status_update", [
            this.pos.config.id,
            order.id,
            status,
            code,
        ]);
        return response;
    },

    async _acceptOrder(order) {
        const syncedOrder = this.pos.models["pos.order"].get(order.id);
        const response = await this._updateOrderStatus(syncedOrder, "Acknowledged");
        const status = await this._handleResponse(response, syncedOrder, "acknowledged");
        if (status) {
            await this.pos._sendDeliveryOrderForPreparation(syncedOrder);
            await this._updateScreenState(syncedOrder, "ACTIVE_ORDERS");
            syncedOrder.uiState.orderAcceptTime = luxon.DateTime.now().ts;
        }
    },

    async _rejectOrder(order) {
        if (
            ["deliveroo", "justeat", "hungerstation"].includes(
                order.delivery_provider_id.technical_name
            )
        ) {
            return this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t(`Rejecting this order is not allowed for "%(providerName)s"`, {
                    providerName: order.delivery_provider_id.name,
                }),
            });
        }
        this.dialog.add(SelectionPopup, {
            title: _t("Reject Order"),
            list: [
                { id: 1, item: "item_out_of_stock", label: _t("Product is out of Stock") },
                { id: 2, item: "store_closed", label: _t("Store is Closed") },
                { id: 3, item: "store_busy", label: _t("Store is Busy") },
                { id: 4, item: "rider_not_available", label: _t("Rider is Not Available") },
                { id: 5, item: "invalid_item", label: _t("Invalid Product") },
                { id: 6, item: "out_of_delivery_radius", label: _t("Out of Delivery Radius") },
                { id: 7, item: "connectivity_issue", label: _t("Connectivity Issue") },
                { id: 8, item: "total_missmatch", label: _t("Total Missmatch") },
                { id: 9, item: "option_out_of_stock", label: _t("Variants/Addons out of Stock") },
                { id: 10, item: "invalid_option", label: _t("Invalid Variant/Addons") },
                { id: 11, item: "unspecified", label: _t("Others") },
            ],
            getPayload: async (code) => {
                const last_order_status = order.delivery_status;
                const response = await this._updateOrderStatus(order, "Cancelled", code);
                const status = await this._handleResponse(response, order, "cancelled");
                if (status) {
                    if (
                        Object.keys(order.last_order_preparation_change.lines).length == 0 &&
                        last_order_status !== "placed"
                    ) {
                        if (order.general_note) {
                            order.last_order_preparation_change.generalNote = order.general_note;
                        }
                        await this.pos.checkPreparationStateAndSentOrderInPreparation(order, true);
                    }
                    await this._updateScreenState(order, "ACTIVE_ORDERS");
                    order.uiState.displayed = false;
                    if (order.id === this.pos.get_order()?.id) {
                        const orderList = this._getOrderList();
                        if (orderList.length == 1) {
                            this.pos.add_new_order();
                        } else {
                            this.pos.selectNextOrder();
                        }
                    }
                    await this.pos.deleteOrders([order]);
                    this.pos.removeOrder(order, true);
                }
            },
        });
    },

    async _doneOrder(order) {
        const response = await this._updateOrderStatus(order, "Food Ready");
        const status = await this._handleResponse(response, order, "food_ready");
        if (status) {
            await this._updateScreenState(order, "SYNCED", "DONE");
        }
        await this.pos.data.searchRead("pos.order", [["id", "=", order.id]]);

        // make sure the order is identified as paid.
        order = this.pos.models["pos.order"].get(order.id);
        this.state.selectedOrderUuid = order.uuid;
        order.set_screen_data({ name: "" });
    },

    async _dispatchOrder(order) {
        const response = await this._updateOrderStatus(order, "Dispatched");
        await this._handleResponse(response, order, "dispatched");
    },

    async _completeOrder(order) {
        const response = await this._updateOrderStatus(order, "Completed");
        await this._handleResponse(response, order, "completed");
    },

    async _onInfoOrder(order) {
        this.dialog.add(orderInfoPopup, {
            order: order,
            order_status: this.order_status,
        });
    },

    /**
     * @override
     * Return results based on upState.
     */
    getFilteredOrderList() {
        const orders = super.getFilteredOrderList();
        if (!this.state.upState) {
            return orders;
        }

        const statusMapping = {
            NEW: "placed",
            ONGOING: "acknowledged",
            DONE: ["food_ready", "dispatched", "completed"],
        };

        const filteredOrders = orders.filter((order) => {
            if (this.state.upState === "DONE") {
                return statusMapping.DONE.includes(order.delivery_status);
            }
            return order.delivery_status === statusMapping[this.state.upState];
        });

        return filteredOrders;
    },

    fetchOrderOtp() {
        return JSON.parse(this.order.delivery_json)?.order?.details?.ext_platforms?.[0].id;
    },

    /**
     * @override
     */
    getDate(order) {
        if (order?.delivery_identifier) {
            return luxon.DateTime.fromFormat(order.date_order, "yyyy-MM-dd HH:mm:ss", {
                zone: "utc",
            })
                .setZone("local")
                .toFormat("MM/dd/yyyy HH:mm:ss");
        }
        return super.getDate(order);
    },

    /**
     * @override
     */
    async onFilterSelected(selectedFilter) {
        if (this.state.upState && this.state.filter != selectedFilter) {
            this.state.upState = "";
        }
        super.onFilterSelected(selectedFilter);
    },

    /**
     * @override
     */
    async onSearch(search) {
        if (this.state.upState && this.state.search != search) {
            this.state.upState = "";
        }
        super.onSearch(search);
    },

    /**
     * @override
     */
    postRefund(destinationOrder) {
        destinationOrder.isDeliveryRefundOrder = this.getSelectedOrder()?.delivery_identifier
            ? true
            : false;
        return super.postRefund(destinationOrder);
    },
});
