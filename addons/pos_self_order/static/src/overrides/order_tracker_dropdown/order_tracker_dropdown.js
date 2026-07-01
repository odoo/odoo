import { useEffect, proxy } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { OrderTrackerDropdown } from "@point_of_sale/app/components/order_tracker_dropdown/order_tracker_dropdown";

patch(OrderTrackerDropdown.prototype, {
    setup() {
        super.setup();
        this.state = proxy({
            countdown: "",
            activeSelfSnoozedRecord: this.pos.getActiveSnooze("self-ordering"),
        });

        useEffect(
            () => {
                // If self-service items are currently snoozed, calculate the remaining countdown time and refresh it every minute.
                if (this.state.activeSelfSnoozedRecord) {
                    this.updateSelfCountdown();
                    const interval = setInterval(() => this.updateSelfCountdown(), 60000);
                    return () => {
                        clearInterval(interval);
                    };
                }
            },
            () => [this.state.activeSelfSnoozedRecord]
        );
    },
    getClass(type, state) {
        let classes = super.getClass(type, state);
        if (type == "SELF" && state == "NEW") {
            classes += " pe-none";
        }
        return classes;
    },
    get externalOrderSummary() {
        const externalOrderSummary = super.externalOrderSummary;
        if (this.pos.config.self_ordering_mode === "mobile") {
            return [
                {
                    type: "SELF",
                    imageUrl: "/web/image?model=pos.config&field=logo&id=" + this.pos.config.id,
                    new: 0, // All self-orders are sent directly to the kitchen!
                    ongoing: this.pos.models["pos.order"].filter(
                        (o) => o.source == "mobile" && o.state == "draft"
                    ).length,
                    done: this.pos.selfOrderCount,
                    onToggle: () => this.snoozeSelfOrdering(),
                    isChecked: !this.state.activeSelfSnoozedRecord?.id,
                    counter: this.state.countdown,
                },
                ...externalOrderSummary,
            ];
        }
        return externalOrderSummary;
    },
    updateSelfCountdown() {
        [this.state.countdown, this.state.activeSelfSnoozedRecord] = this.pos.getSnoozeCountdown(
            this.state.activeSelfSnoozedRecord
        );
        // We only need hh:mm format for self order countdown
        this.state.countdown = this.state.countdown.split(":").slice(0, 2).join(":");
    },
    async snoozeSelfOrdering() {
        // If already snoozed, unsnooze self-order service.
        if (this.state.activeSelfSnoozedRecord) {
            this.pos.unSnoozeItem(this.state.activeSelfSnoozedRecord, async () => {
                this.state.activeSelfSnoozedRecord = undefined;
                this.state.countdown = "";
                await this.pos.data.call("pos.config", "notify_self_order", [this.pos.config.id]);
            });
            return;
        }
        this.pos.snoozeItem("self-ordering", async (record) => {
            this.state.activeSelfSnoozedRecord = record;
            await this.pos.data.call("pos.config", "notify_self_order", [this.pos.config.id]);
        });
        return;
    },
});
