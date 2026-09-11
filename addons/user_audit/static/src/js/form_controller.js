/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
patch(FormController.prototype, 'list-controller-patch', {
    setup() {
        this._super.apply(arguments);
        this.orm = useService("orm");
    },
    //For managing save button click
    async saveButtonClicked(params = {}) {
        this.disableButtons();
        const record = this.model.root;
        let saved = false;
        if (this.props.saveRecord) {
            saved = await this.props.saveRecord(record, params);
        } else {
            saved = await record.save();
        }
        this.enableButtons();
        if (saved && this.props.onSave) {
            this.props.onSave(record, params);
        }
        var resModel = record.resModel;
        var resId = record.resId;
        this.orm.call(
                    "user.audit",
                    "create_audit_log_for_write",
                    [resModel,resId],
                    ).then(function(data) {
                    })
        return saved;
    },
    //For managing create operation
     async create() {
        await this.model.root.askChanges(); // ensures that isDirty is correct
        let canProceed = true;
        if (this.model.root.isDirty) {
            canProceed = await this.model.root.save({
                stayInEdition: true,
                useSaveErrorDialog: true,
            });
        }
        if (canProceed) {
            this.disableButtons();
            await this.model.load({ resId: null });
            this.enableButtons();
        }
        var resModel = this.model.root.resModel;
         this.orm.call(
                    "user.audit",
                    "create_audit_log_for_create",
                    [resModel],
                    ).then(function(data) {
                    })
    },
    //for managing delete operation
    async deleteRecord() {
      var resModel = this.model.root.resModel;
        var resId = this.model.root.resId;
        const dialogProps = {
            body: this.env._t("Are you sure you want to delete this record?"),
            confirm: async () => {
                await this.model.root.delete();
                this.orm.call(
                    "user.audit",
                    "create_audit_log_for_delete",
                    [resModel,resId],
                    ).then(function(data) {
                    })
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            },
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }
    })
