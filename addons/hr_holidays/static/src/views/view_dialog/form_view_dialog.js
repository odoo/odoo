import { onWillStart } from "@odoo/owl";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

import { useLeaveCancelWizard } from "../hooks";

export class TimeOffDialogFormController extends FormController {
    static props = {
        ...FormController.props,
        onCancelLeave: Function,
        onRecordDeleted: Function,
        onLeaveCancelled: Function,
    };

    setup() {
        super.setup();
        this.leaveCancelWizard = useLeaveCancelWizard();
        this.orm = useService("orm");
        this.action = useService("action");
        onWillStart(async () => {
            this.isHrHolidaysUser = (await user.hasGroup("hr_holidays.group_hr_holidays_user"));
        });
    }

    get record() {
        return this.model.root;
    }

    async onClick(action) {
        const args = action === "action_approve" ? [this.record.resId, false] : [this.record.resId];
        await this.orm.call("hr.leave", action, args);
        this.save(this.record._changes);
    }

    get canSave() {
        return (!this.isOwnLeave && this.record.isNew) || (this.isOwnLeave && this.record.data.state === 'confirm')
    }

    get canApprove() {
        return this.record.data.can_approve && !this.record.isNew;
    }

    get canClose() {
        return this.record.isNew || !(this.record.data.state === 'confirm' && this.canRefuse)
    }

    get canValidate() {
        return this.record.data.can_validate && !this.record.isNew;
    }

    get canRefuse() {
        return this.record.data.can_refuse && !this.record.isNew;
    }

    get isOwnLeave() {
        return this.record.data.user_id && this.record.data.user_id[0] === user.userId;
    }

    get approveClassName(){
        return this.canSave ? "btn btn-secondary" : "btn btn-primary";
    }

    get validateClassName(){
        return this.canSave ? "btn btn-secondary" : "btn btn-primary";
    }

    get refuseClassName(){
        return (this.canValidate || this.canApprove) ? "btn btn-secondary" : "btn btn-primary";
    }

    deleteRecord() {
        this.props.onRecordDeleted(this.record);
        this.props.onCancelLeave();
    }

    cancelRecord() {
        this.deleteRecord();
        this.leaveCancelWizard(this.record.resId, () => {
            this.props.onLeaveCancelled();
        });
    }

    get canCancel() {
        return this.record.data.can_cancel;
    }

    get canDelete() {
        return this.record.data.state === 'confirm';
    }
}

registry.category("views").add("timeoff_dialog_form", {
    ...formView,
    Controller: TimeOffDialogFormController,
});

export class TimeOffFormViewDialog extends FormViewDialog {
    static props = {
        ...TimeOffFormViewDialog.props,
        onRecordDeleted: Function,
        onLeaveCancelled: Function,
    };

    setup() {
        super.setup();

        this.viewProps = Object.assign(this.viewProps, {
            jsClass: "timeoff_dialog_form",
            buttonTemplate: "hr_holidays.FormViewDialog.buttons",
            onCancelLeave: () => {
                this.props.close();
            },
            onRecordDeleted: (record) => {
                this.props.onRecordDeleted(record);
            },
            onLeaveCancelled: this.props.onLeaveCancelled.bind(this),
        });
    }
}
