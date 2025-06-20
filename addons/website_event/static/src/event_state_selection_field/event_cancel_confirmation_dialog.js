import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class EventConfirmationDialog extends ConfirmationDialog {
    static template = "website_event.EventConfirmationDialog";
    static props = {
        ...ConfirmationDialog.props,
        unpublishEvent: { type: Function },
    };

    async _unpublishEvent() {
        if (this.props.unpublishEvent) {
            await this.props.unpublishEvent();
        }
    }
}
