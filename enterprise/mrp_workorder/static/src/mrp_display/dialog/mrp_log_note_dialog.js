/** @odoo-module */
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { TextField } from "@web/views/fields/text/text_field";

export class MrpLogNoteDialog extends ConfirmationDialog {
    static template = "mrp_workorder.MrpLogNoteDialog";
    static props = {
        ...ConfirmationDialog.props,
        record: Object,
        reload: { type: Function, optional: true },
    }
    static components = {
        ...ConfirmationDialog.components,
        TextField,
    }

    async _cancel() {
        this.props.record.save();
        this.props.close();
    }
}
