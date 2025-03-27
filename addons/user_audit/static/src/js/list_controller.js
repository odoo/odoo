/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListController } from '@web/views/list/list_controller';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
patch(ListController.prototype, 'list-controller-patch', {
    setup() {
        this._super.apply(arguments);
        this.orm = useService("orm");
    },
    // For tracking delete operation
    async createRecord({ group } = {}) {
        const list = (group && group.list) || this.model.root;
        var resModel = this.model.rootParams.resModel;
        if (this.editable) {
            if (!(list instanceof DynamicRecordList)) {
                throw new Error("List should be a DynamicRecordList");
            }
            if (list.editedRecord) {
                await list.editedRecord.save();
            }
            if (!list.editedRecord) {
                await (group || list).createRecord({}, this.editable === "top");
            }
            this.render();
        } else {
            this.orm.call(
                    "user.audit",
                    "create_audit_log_for_create",
                    [resModel],
                    ).then(function(data) {
                    })
            await this.props.createRecord();
        }
                },
                //for tracking write operation
    async openRecord(record) {
        if (this.archInfo.openAction) {
            this.actionService.doActionButton({
                name: this.archInfo.openAction.action,
                type: this.archInfo.openAction.type,
                resModel: record.resModel,
                resId: record.resId,
                resIds: record.resIds,
                context: record.context,
                onClose: async () => {
                    await record.model.root.load();
                    record.model.notify();
                },
            });
        } else {
            const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
            this.props.selectRecord(record.resId, { activeIds });
        }
        var resModel = record.resModel;
        var resId = record.resId
        this.orm.call(
                "user.audit",
                "create_audit_log_for_read",
                [resModel,resId],
                ).then(function(data) {
                })
    },
    //For managing delete of multiple records
    async onDeleteSelectedRecords() {
        const root = this.model.root;
        var resId = root.records[0].resId
        const body =
            root.isDomainSelected || root.selection.length > 1
                ? this.env._t("Are you sure you want to delete these records?")
                : this.env._t("Are you sure you want to delete this record?");
        const dialogProps = {
            body,
            confirm: async () => {
                const total = root.count;
                const resIds = await this.model.root.deleteRecords();
                 var resModel = this.model.root.resModel;
                 this.orm.call(
                            "user.audit",
                            "create_audit_log_for_delete",
                            [resModel,resId],
                            ).then(function(data) {
                            })
                this.model.notify();
                if (
                    root.isDomainSelected &&
                    resIds.length === session.active_ids_limit &&
                    resIds.length < total
                ) {
                    this.notificationService.add(
                        sprintf(
                            this.env._t(
                                `Only the first %s records have been deleted (out of %s selected)`
                            ),
                            resIds.length,
                            total
                        ),
                        { title: this.env._t("Warning") }
                    );
                }
            },
            cancel: () => {},
        };
        this.dialogService.add(ConfirmationDialog, dialogProps);
    }
    })
