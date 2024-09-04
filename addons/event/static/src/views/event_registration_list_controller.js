import { EventRegistrationSummaryDialog } from "@event/client_action/event_registration_summary_dialog";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export default class EventRegistrationListController extends ListController {

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");

        onMounted(this.hideSystray);
        onWillUnmount(this.showSystray);
    }

    async openRecord(record, mode) {
        const barcode = record.data.barcode
        const eventId = record.data.event_id[0]

        const result = await this.orm.call("event.registration", "register_attendee", [], {
            barcode: barcode,
            event_id: eventId,
        });

        this.dialog.add(
            EventRegistrationSummaryDialog,
            {
                registration: result,
                model: this.model
            }
        )
    }

    hideSystray() {
        if (document.querySelector('.o_event_registration_view_tree')) {
            document.querySelector('.o_menu_systray').classList.add('d-none');
        }
    }

    showSystray() {
        if (document.querySelector('.o_event_registration_view_tree')) {
            document.querySelector('.o_menu_systray').classList.remove('d-none');
        }
    }
}

registry.category("views").add("registration_dialog_list", {
    ...listView,
    Controller: EventRegistrationListController,
});
