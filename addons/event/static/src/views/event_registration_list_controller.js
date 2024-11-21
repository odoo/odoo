import { EventRegistrationSummaryDialog } from "@event/client_action/event_registration_summary_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export class EventRegistrationListController extends ListController {

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    async openRecord(record) {
        if (this.props.context.is_registration_desk_view) {
            const barcode = record.data.barcode;
            const eventId = record.data.event_id[0];

            const result = await this.orm.call("event.registration", "register_attendee", [], {
                barcode: barcode,
                event_id: eventId,
            });

            this.dialog.add(
                EventRegistrationSummaryDialog,
                {
                    model: this.model,
                    registration: result
                }
            );
        } else {
            return super.openRecord(record);
        }
    }
}

export const EventRegistrationListView = {
    ...listView,
   Controller: EventRegistrationListController,
}

registry.category("views").add("registration_summary_dialog_list", EventRegistrationListView);
