import { props, t } from "@odoo/owl";
import { FormViewDialog, formViewDialogProps } from "@web/views/view_dialogs/form_view_dialog";

export const massMailingFormViewDialogProps = {
    ...formViewDialogProps,
    onRecordSavedForLater: t.function().optional(() => () => {}),
};

export class MailingFilterFormViewDialog extends FormViewDialog {
    props = props(massMailingFormViewDialogProps);
    setup() {
        super.setup();
        Object.assign(this.viewProps, {
            buttonDialogTemplate: "mass_mailing.MailingFilterFormViewDialog.buttons",
            saveRecord: async (record, params) => {
                let saved;
                if (this.props.onRecordSave) {
                    saved = await this.props.onRecordSave(record);
                } else {
                    saved = await record.save({ reload: false });
                    if (saved) {
                        this.currentResId = record.resId;
                        if (params.isSaveForLater) {
                            await this.props.onRecordSavedForLater(record);
                        } else {
                            await this.props.onRecordSaved(record);
                        }
                    }
                }
                if (saved) {
                    await this.onRecordSaved(record, params);
                }
                return saved;
            },
        });
    }
}
