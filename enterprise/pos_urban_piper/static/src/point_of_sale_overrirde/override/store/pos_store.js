import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    /**
     * @override
     */
    async setup() {
        await super.setup(...arguments);
        this.delivery_order_count = {};
        this.enabledProviders = {};

        // Init provider states from other sources
        await this.initProviderStatus();

        this.data.connectWebSocket("DELIVERY_ORDER_COUNT", async (order_id) => {
            await this._fetchUrbanpiperOrderCount(order_id);
        });
        this.data.connectWebSocket("STORE_ACTION", async (data) => {
            await this._fetchStoreAction(data);
        });
        this.data.connectWebSocket("URBAN_PIPER_PROVIDER_STATES", async (data) => {
            this.enabledProviders = data;
        });
        if (this.config.module_pos_urban_piper && this.config.urbanpiper_store_identifier) {
            await this._fetchUrbanpiperOrderCount(false);
        }
    },

    async saveProviderState(newStates = {}) {
        this.enabledProviders = await this.data.call(
            "pos.config",
            "set_urban_piper_provider_states",
            [this.config.id, JSON.stringify(newStates)]
        );
    },

    async getProviderState() {
        const provideState = await this.data.call("pos.config", "get_urban_piper_provider_states", [
            this.config.id,
        ]);
        return provideState || {};
    },

    async initProviderStatus() {
        // If certain providers are not yet in the status cache, we create it and set it to true.
        let changed = false;
        this.enabledProviders = await this.getProviderState();

        for (const provider of this.config.urbanpiper_delivery_provider_ids) {
            const name = provider.technical_name;
            const currentValue = this.enabledProviders[name];
            const newValue = currentValue === undefined ? true : this.enabledProviders[name];
            if (currentValue === undefined) {
                changed = true; // Initialize provider state to true
            }
            this.enabledProviders[name] = newValue;
        }

        if (changed) {
            await this.saveProviderState(this.enabledProviders);
        }
    },

    async updateStoreStatus(status = false, providerName = false) {
        if (this.config.module_pos_urban_piper && this.config.urbanpiper_store_identifier) {
            await this.data.call("pos.config", "update_store_status", [this.config.id, status], {
                context: {
                    providerName: providerName,
                },
            });
        }
    },

    async getServerOrders() {
        if (this.config.module_pos_urban_piper && this.config.urbanpiper_store_identifier) {
            await this.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                ["session_id", "=", this.session.id],
                [
                    "delivery_provider_id",
                    "in",
                    this.config.urbanpiper_delivery_provider_ids.map((provider) => provider.id),
                ],
            ]);
        }
        return await super.getServerOrders(...arguments);
    },

    _fetchStoreAction(data) {
        const params = {
            type: "success",
            sticky: false,
        };
        let message = "";

        if (data.status) {
            this.enabledProviders[data.platform] = data.action === "enable";
            this.saveProviderState(this.enabledProviders);
        }
        // Prepare notification message
        if (!data.status) {
            params.type = "danger";
            message = _t("Error occurred while updating " + data.platform + " status.");
        } else if (data.action === "enable") {
            message = _t(this.config.name + " is online on " + data.platform + ".");
        } else if (data.action === "disable") {
            message = _t(this.config.name + " is offline on " + data.platform + ".");
        }

        if (message) {
            this.notification.add(message, params);
        }
    },

    async _fetchUrbanpiperOrderCount(order_id) {
        try {
            await this.getServerOrders();
        } catch {
            this.notification.add(_t("Order does not load from server"), {
                type: "warning",
                sticky: false,
            });
        }
        const response = await this.data.call(
            "pos.config",
            "get_delivery_data",
            [this.config.id],
            {}
        );
        this.delivery_order_count = response.delivery_order_count;
        this.delivery_providers = response.delivery_providers;
        this.total_new_order = response.total_new_order || 0;
        const deliveryOrder = order_id ? this.models["pos.order"].get(order_id) : false;
        if (!deliveryOrder) {
            return;
        }
        if (deliveryOrder.delivery_status === "acknowledged") {
            await this._sendDeliveryOrderForPreparation(deliveryOrder);
        } else if (deliveryOrder.delivery_status === "placed") {
            this.sound.play("notification");
            this.notification.add(_t("New online order received."), {
                type: "success",
                sticky: false,
                buttons: [
                    {
                        name: _t("Review Orders"),
                        onClick: () => {
                            const stateOverride = {
                                search: {
                                    fieldName: "DELIVERYPROVIDER",
                                    searchTerm: deliveryOrder?.delivery_provider_id.name,
                                },
                                filter: "ACTIVE_ORDERS",
                            };
                            this.set_order(deliveryOrder);
                            if (this.mainScreen.component?.name == "TicketScreen") {
                                this.env.services.ui.block();
                                if (this.config.module_pos_restaurant) {
                                    this.showScreen("FloorScreen");
                                } else {
                                    this.showScreen("ProductScreen");
                                }
                                setTimeout(() => {
                                    this.showScreen("TicketScreen", { stateOverride });
                                    this.env.services.ui.unblock();
                                }, 300);
                                return;
                            }
                            return this.showScreen("TicketScreen", { stateOverride });
                        },
                    },
                ],
            });
        }
    },

    async _sendDeliveryOrderForPreparation(deliveryOrder) {
        if (
            deliveryOrder.last_order_preparation_change.urbanpiper_printed ||
            deliveryOrder.isFutureOrder()
        ) {
            return;
        }
        let isReadyToPrint = true;
        try {
            await this.data.call("pos.order", "mark_urbanpiper_prep_order_as_printed", [
                deliveryOrder.id,
            ]);
        } catch {
            isReadyToPrint = false;
        }
        if (isReadyToPrint) {
            await this.sendOrderInPreparationUpdateLastChange(deliveryOrder);
        }
    },

    /**
     * @override
     */
    addOrderIfEmpty() {
        if (
            !this.get_order() ||
            (this.get_order().delivery_identifier && this.get_order().state == "paid")
        ) {
            this.add_new_order();
            return;
        }
        return super.addOrderIfEmpty(...arguments);
    },

    async goToBack() {
        this.addPendingOrder([this.selectedOrder.id]);
        await this.syncAllOrders();
        this.showScreen("TicketScreen");
        if (this.selectedOrder.delivery_status !== "placed") {
            try {
                await this.checkPreparationStateAndSentOrderInPreparation(this.selectedOrder);
            } catch {
                this.notification.add(_t("Error to send in preparation display."), {
                    type: "warning",
                    sticky: false,
                });
            }
        }
    },

    getPrintingChanges(order, diningModeUpdate) {
        let changes = super.getPrintingChanges(order, diningModeUpdate);
        if (order.delivery_provider_id) {
            changes = {
                ...changes,
                delivery_provider_id: order.delivery_provider_id,
                order_otp: JSON.parse(order.delivery_json)?.order?.details?.ext_platforms?.[0].id,
                prep_time: order.prep_time,
            };
        }
        return changes;
    },
});
