/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { useUnlinkCalendarEvents } from "@calendar/views/hooks";

export class CaledarListController extends ListController {
    setup() {
        super.setup();
        this.unlinkCalendarEvents = useUnlinkCalendarEvents({ model: this.model });
    }

    get modelOptions() {
        return {
            ...super.modelOptions,
            lazy: false,
        };
    }

    async onDeleteSelectedRecords() {
        this.unlinkCalendarEvents({
            records: this.model.root.selection,
            defaultAction: () => this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps),
        });
    }
}
