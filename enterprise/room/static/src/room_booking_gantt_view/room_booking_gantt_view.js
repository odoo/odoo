import { ganttView } from "@web_gantt/gantt_view";
import { registry } from "@web/core/registry";

class RoomBookingGanttController extends ganttView.Controller {
     /**
     * @override
     * Show content helper if no records have been found/loaded
     */
     get showNoContentHelp() {
        return !this.model.data.count;
    }

    /**
     * @override
     * When creating a new booking using the "new" button, use the current time
     * as start datetime and the current time plus one hour as stop datetime.
     */
    onAddClicked() {
        const start = luxon.DateTime.now();
        const stop = start.plus({ hour: 1 });
        const context = this.model.getDialogContext({ start, stop, withDefault: true });
        this.create(context);
    }
}

class RoomBookingGanttModel extends ganttView.Model {
    /**
     * @override
     * Add some context key to the search to show rooms that have no bookings
     */
    load(searchParams) {
        return super.load({
            ...searchParams,
            context: { ...searchParams.context, room_booking_gantt_show_all_rooms: true },
        });
    }
}

const roomBookingGanttView = {
    ...ganttView,
    Controller: RoomBookingGanttController,
    Model: RoomBookingGanttModel,
};

registry.category("views").add("room_booking_gantt", roomBookingGanttView);
