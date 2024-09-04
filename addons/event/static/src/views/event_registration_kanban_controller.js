import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { EventRegistrationSummaryDialog } from "@event/client_action/event_registration_summary_dialog";
import { onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export default class EventRegistrationKanbanController extends KanbanController {

    setup() {
        super.setup()
        this.dialog = useService("dialog");
        this.orm = useService("orm")
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
        this.observer = new MutationObserver((mutations) => {
            document.querySelector('.o_menu_systray').classList.add('d-none');
            this.observer.disconnect();
        });
        this.observer.observe(document.body, { childList: true, subtree: true });
    }

    showSystray() {
        if (document.querySelector('.o_event_attendee_kanban_view')) {
            document.querySelector('.o_menu_systray').classList.remove('d-none');
        }
    }
}

registry.category("views").add("registration_dialog_kanban", {
    ...kanbanView,
    Controller: EventRegistrationKanbanController,
});
