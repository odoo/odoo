/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { useDeleteCalendarEvents } from "@calendar/views/hooks";

export class CaledarListController extends ListController {
    setup() {
        super.setup();
        this.deleteCalendarEvents = useDeleteCalendarEvents({ model: this.model });
    }

    get modelOptions() {
        return {
            ...super.modelOptions,
            lazy: false,
        };
    }

    async onDeleteSelectedRecords() {
        this.deleteCalendarEvents({
            records: this.model.root.selection,
            deleteConfirmationDialogProps: this.deleteConfirmationDialogProps,
        });
    }
}
