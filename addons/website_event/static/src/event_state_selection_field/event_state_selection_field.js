import { _t } from "@web/core/l10n/translation";
import { EventConfirmationDialog } from "./event_cancel_confirmation_dialog";
import { EventStateSelection } from "@event/event_state_selection_field/event_state_selection_field"
import { patch } from "@web/core/utils/patch";
import { useService } from '@web/core/utils/hooks';


patch(EventStateSelection.prototype, {

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.website = useService('website');
    },
    
    async updateRecord(value) {
        if (value !== 'cancel' || this.currentValue === 'cancel') {
            return super.updateRecord(value);
        }

        this.dialog.add(EventConfirmationDialog, {
            title: _t("Are you sure you want to cancel this event?"),
            body: _t("It will still be visible on your website, but will feature a 'Cancelled' banner.\nAny scheduled communication will be blocked.\n\nDon't forget to notify attendees who already registered."),
            confirmLabel: _t("Proceed"),
            confirm: async () => {
                await this.props.record.update({ [this.props.name]: value }, { save: this.props.autosave });
            },
            unpublishEvent: async () => {
                await this.orm.write(this.props.record.resModel, [this.props.record.resId], { is_published: false });
                await this.website.goToWebsite({ path: `event/${this.props.record.resId}` });
            },
            cancelLabel: _t("Go back"),
            cancel: () => {},
        });
    }
});
