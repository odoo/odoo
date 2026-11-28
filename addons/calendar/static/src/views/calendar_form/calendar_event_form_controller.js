import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { FormController } from "@web/views/form/form_controller";
import { useArchiveOrUnlinkCalendarEvent } from "@calendar/views/hooks";
import { useAskRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { useService } from "@web/core/utils/hooks";
import { executeButtonCallback } from "@web/views/view_button/view_button_hook";

export class CalendarEventFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy();
        this.archiveOrUnlinkCalendarEvent = useArchiveOrUnlinkCalendarEvent();
    }

    /**
     * This method is meant to be overridden.
     */
    shouldUseArchiveWizard() {
        return true;
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable && this.shouldUseArchiveWizard()) {
            actionMenuItems.archive.callback = async () => {
                const record = this.model.root;
                await this.archiveOrUnlinkCalendarEvent({
                    requestedAction: "archive",
                    resId: record.resId,
                    isDraft: record.data.is_draft,
                    partnerIds: record.data.partner_ids.resIds,
                    recurrency: record.data.recurrency,
                    start: record.data.start,
                    defaultAction: () => this.dialogService.add(ConfirmationDialog, this.archiveDialogProps),
                });
            };
        }
        return actionMenuItems;
    }

    askEventConfirmation() {
        return new Promise((resolve) => {
            this.dialogService.add(
                ConfirmationDialog,
                {
                    title: _t("Confirm event"),
                    body: _t("Applying a recurrence on a draft requires the event to be confirmed.\nAttendees will be notified upon confirmation.\nConfirm ?"),
                    confirmLabel: _t("Confirm"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                },
                {
                    onClose: () => resolve(false),
                }
            );
        });
    }

    askRecurrenceDeletion() {
        return new Promise((resolve) => {
            this.dialogService.add(
                ConfirmationDialog,
                {
                    title: _t("Disable recurrence"),
                    body: _t("Turning off the recurrence on this event will delete any occurence of it.\nProceed ?"),
                    confirmLabel: _t("Disable"),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                },
                {
                    onClose: () => resolve(false),
                }
            );
        });
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        const action = clickParams.name;
        if (action === "clear_videocall_location") {
            this.model.root.clearLocation();
            return false;
        } else if (action === "set_discuss_videocall_location") {
            this.model.root.setLocation();
            return false;
        }
        return super.beforeExecuteActionButton(...arguments);
    }

    /**
     * @override
     */
    async deleteRecord() {
        const record = this.model.root;
        const rootValues = record._values;
        if (rootValues.attendees_count == 1 && rootValues.user_id.id !== rootValues.partner_ids._currentIds[0]) {
            await this._archiveRecord(record);
        } else {
            await this.archiveOrUnlinkCalendarEvent({
                requestedAction: "unlink",
                resId: record.resId,
                isDraft: record.data.is_draft,
                partnerIds: record.data.partner_ids.resIds,
                recurrency: record.data.recurrency,
                start: record.data.start,
                defaultAction: () => this.deleteRecordsWithConfirmation(this.deleteConfirmationDialogProps),
                nextAction: { type: "ir.actions.act_url", target: "self", url: "/odoo/calendar" },
            });
        }
    }

    /**
     * Archives a calendar event record.
     */
    async _archiveRecord(record) {
        let recurrenceUpdate = false;
        if (record.data.recurrency) {
            recurrenceUpdate = await this.askRecurrenceUpdatePolicy();
        }
        await this.orm.call(this.model.root.resModel, "action_mass_archive", [
            [record.resId], recurrenceUpdate
        ]);
        this.env.config.historyBack();
    }

    async save(params) {
        const record = this.model.root;
        let recurrenceUpdate = false;
        let saved = false;
        if (record.data.is_draft && record.data.recurrency) {
            const confirmEvent = await this.askEventConfirmation();
            if (!confirmEvent) {
                return saved;
            } else {
                record.update({
                    "is_draft": false,
                    "show_as": 'busy',
                });
            }
        }
        if (record.data.recurrence_id && !record.data.recurrency) {
            const disableRecurrence = await this.askRecurrenceDeletion();
            if (!disableRecurrence) {
                return saved;
            } else {
                recurrenceUpdate = "all_events"
                record.update({"recurrence_update": recurrenceUpdate});
            }
        } else if (record.data.recurrence_id) {
            recurrenceUpdate = await this.askRecurrenceUpdatePolicy();
            record.update({"recurrence_update": recurrenceUpdate});
        }
        if (this.props.saveRecord) {
            saved = await this.props.saveRecord(record, params);
        } else {
            saved = await record.save({
                onError: (error, options) => this.onSaveError(error, options, false),
                ...params,
            });
        }
        if (saved && this.props.onSave) {
            this.props.onSave(record, params);
        }
        return saved;
    }

    saveButtonClicked(params = {}) {
        return executeButtonCallback(this.ui.activeElement, () => this.save(params));
    }
}
