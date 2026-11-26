import { useEffect, signal, t } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { OrderTrackerDropdown } from "@point_of_sale/app/components/order_tracker_dropdown/order_tracker_dropdown";
import { ConnectionLostError } from "@web/core/network/rpc";

patch(OrderTrackerDropdown.prototype, {
    setup() {
        super.setup();
        this.selfSnoozeCountdown = signal("", { type: t.string().optional("") });

        useEffect(() => {
            const activeSnooze = this.pos.getActiveSnooze("self-ordering");
            if (activeSnooze) {
                this.updateSelfCountdown();
                const interval = setInterval(() => this.updateSelfCountdown(), 60000);
                return () => {
                    clearInterval(interval);
                };
            } else {
                this.selfSnoozeCountdown.set("");
            }
        });
    },
    getClass(type) {
        let classes = super.getClass(type);
        if (type === "SOURCE") {
            classes += " pe-none";
        }
        return classes;
    },
    get externalOrderSummary() {
        const externalOrderSummary = super.externalOrderSummary;
        if (this.pos.config.self_ordering_mode === "mobile") {
            const activeSnooze = this.pos.getActiveSnooze("self-ordering");
            const doneOrderIds = new Set(this.pos.paidSelfOrderIds);
            let ongoing = 0;
            for (const order of this.pos.models["pos.order"].getAll()) {
                if (order.source !== "mobile") {
                    continue;
                }
                if (order.state === "draft") {
                    ongoing++;
                } else if (["paid", "done"].includes(order.state)) {
                    doneOrderIds.add(order.id);
                }
            }
            return [
                {
                    type: "SOURCE",
                    searchTerm: "mobile",
                    imageUrl: this.pos.config.receiptLogoUrl,
                    new: 0, // All self-orders are sent directly to the kitchen!
                    ongoing,
                    done: doneOrderIds.size,
                    onToggle: () => this.snoozeSelfOrdering(),
                    isChecked: !activeSnooze?.id,
                    counter: this.selfSnoozeCountdown(),
                },
                ...externalOrderSummary,
            ];
        }
        return externalOrderSummary;
    },
    async goToOrders(serviceName, state, searchTerm = "") {
        if (serviceName === "SOURCE" && state === "DONE") {
            await this.loadPaidSelfOrders();
        }
        return super.goToOrders(serviceName, state, searchTerm);
    },
    async loadPaidSelfOrders() {
        const orderModel = this.pos.models["pos.order"];
        const missingIds = this.pos.paidSelfOrderIds.filter((id) => !orderModel.get(id));
        if (!missingIds.length) {
            return;
        }
        try {
            await this.pos.data.loadServerOrders([["id", "in", missingIds]]);
        } catch (error) {
            if (!(error instanceof ConnectionLostError)) {
                throw error;
            }
        }
    },
    updateSelfCountdown() {
        const activeSnooze = this.pos.getActiveSnooze("self-ordering");
        if (activeSnooze) {
            const [countdown] = this.pos.getSnoozeCountdown(activeSnooze);
            this.selfSnoozeCountdown.set(countdown.split(":").slice(0, 2).join(":"));
        }
    },
    async snoozeSelfOrdering() {
        const activeSnooze = this.pos.getActiveSnooze("self-ordering");
        if (activeSnooze) {
            this.pos.unSnoozeItem(activeSnooze, async () => {
                this.selfSnoozeCountdown.set("");
                await this.pos.data.call("pos.config", "notify_session_state_changed", [
                    this.pos.config.id,
                ]);
            });
            return;
        }
        this.pos.snoozeItem("self-ordering", async () => {
            await this.pos.data.call("pos.config", "notify_session_state_changed", [
                this.pos.config.id,
            ]);
        });
        return;
    },
});
