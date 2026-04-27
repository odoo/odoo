import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket("TABLE_BOOKING", (payload) => {
            const { command, event } = payload;
            if (!event) {
                return;
            }
            if (command === "ADDED") {
                this.models.loadData({ "calendar.event": [event] });
            } else if (command === "REMOVED") {
                this.models["calendar.event"].get(event.id)?.delete?.();
            }
        });
    },
    async manageBookings() {
        this.orderToTransferUuid = null;
        this.showScreen("ActionScreen", { actionName: "ManageBookings" });
        await this.action.doAction(
            await this.data.call("calendar.event", "action_open_booking_gantt_view", [false], {
                context: { appointment_type_id: this.config.raw.appointment_type_id },
            })
        );
    },
    async editBooking(appointment) {
        const action = await this.data.call("calendar.event", "action_open_booking_form_view", [
            appointment.id,
        ]);
        return this.action.doAction(action);
    },
});
