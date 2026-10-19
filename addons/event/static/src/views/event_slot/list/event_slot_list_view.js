import { EventSlotListController } from "@event/views/event_slot/list/event_slot_list_controller";
import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";

export const EventSlotListView = {
    ...listView,
    Controller: EventSlotListController,
};

registry.category("views").add("event_slot_list", EventSlotListView);
