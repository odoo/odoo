/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { useArchiveOrUnlinkCalendarEvents } from "@calendar/views/hooks";

export class CaledarListController extends ListController {
    setup() {
        super.setup();
        this.archiveOrUnlinkCalendarEvents = useArchiveOrUnlinkCalendarEvents();
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.callback = async () => {
                this.archiveOrUnlinkCalendarEvents({
                    requestedAction: "archive",
                    records: this.model.root.selection,
                    defaultAction: () => this.model.root.toggleArchiveWithConfirmation(true, this.archiveDialogProps),
                });
            };
        }
        return actionMenuItems;
    }

    get modelOptions() {
        return {
            ...super.modelOptions,
            lazy: false,
        };
    }
    async onDeleteSelectedRecords() {
        this.archiveOrUnlinkCalendarEvents({
            requestedAction: "unlink",
            records: this.model.root.selection,
            defaultAction: () => this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps),
        });
    }
}
