/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { useCancelCalendarEvents } from "@calendar/views/hooks";

export class CaledarListController extends ListController {
    setup() {
        super.setup();
        this.cancelCalendarEvents = useCancelCalendarEvents();
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.callback = async () => {
                this.cancelCalendarEvents({
                    requestedAction: "cancel",
                    records: this.model.root.selection,
                    fallback: () => this.model.root.toggleArchiveWithConfirmation(true, this.archiveDialogProps),
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
        this.cancelCalendarEvents({
            requestedAction: "delete",
            records: this.model.root.selection,
            fallback: () => this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps),
        });
    }
}
