import { WorkEntryCalendarMultiSelectionButtons } from "@hr_work_entry/views/work_entry_calendar/work_entry_multi_selection_buttons";
import { useWorkEntry } from "@hr_work_entry/views/work_entry_hook";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { CalendarController } from "@web/views/calendar/calendar_controller";
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";


export class WorkEntryCalendarController extends CalendarController {
    static components = {
        ...CalendarController.components,
        MultiSelectionButtons: WorkEntryCalendarMultiSelectionButtons,
    };

    setup() {
        super.setup();
        const { onRegenerateWorkEntries } = useWorkEntry({
            getEmployeeIds: this.getEmployeeIds.bind(this),
            getRange: this.model.computeRange.bind(this.model),
            onClose: this.model.load.bind(this.model),
        });
        this.onRegenerateWorkEntries = onRegenerateWorkEntries;
        this.dialogService = useService("dialog");
    }

    async splitRecord(record) {
        this.dialogService.add(
            FormViewDialog,
            {
                title: _t("Split Work Entry"),
                resModel: "hr.work.entry",
                onRecordSave: async (_record) => {
                    await this.orm.call("hr.work.entry", "action_split", [
                        record.id,
                        {
                            duration: _record.data.duration,
                            work_entry_type_id: _record.data.work_entry_type_id.id,
                            name: _record.data.name,
                        },
                    ]);
                    return true;
                },
                context: {
                    form_view_ref: "hr_work_entry.hr_work_entry_calendar_gantt_view_form",
                    default_duration: record.rawRecord.duration / 2,
                    default_name: record.rawRecord.name,
                    default_work_entry_type_id: record.rawRecord.work_entry_type_id?.[0],
                    default_employee_id: record.rawRecord.employee_id?.[0],
                    default_date: record.rawRecord.date,
                },
                canExpand: false,
            },
            {
                onClose: () => {
                    this.model.load();
                },
            }
        );
    }

    /**
     * @override
     */
    get rendererProps() {
        return {
            ...super.rendererProps,
            splitRecord: this.splitRecord.bind(this),
        };
    }

    getEmployeeIds() {
        return [
            ...new Set(
                Object.values(this.model.records).map((rec) => rec.rawRecord.employee_id[0])
            ),
        ];
    }

    getSelectedRecords(selectedCells) {
        const ids = this.getSelectedRecordIds(selectedCells);
        return Object.values(this.model.records)
            .filter((r) => ids.includes(r.id))
            .map((r) => r.rawRecord);
    }

    /**
     * @override
     */
    prepareMultiSelectionButtonsReactive() {
        const result = super.prepareMultiSelectionButtonsReactive();
        result.userFavoritesWorkEntries = this.model.userFavoritesWorkEntries || [];
        result.onQuickReplace = (values) => this.onMultiReplace(values, this.selectedCells);
        result.onQuickReset = () => this.onResetWorkEntries(this.selectedCells);
        return result;
    }

    /**
     * @override
     */
    updateMultiSelection() {
        super.updateMultiSelection(...arguments);
        this.multiSelectionButtonsReactive.userFavoritesWorkEntries = this.model.userFavoritesWorkEntries || [];
    }

    getDatesWithoutValidatedWorkEntry(selectedCells, records) {
        return this.getDates(selectedCells).filter(
            (d) =>
                !records
                    .filter((r) => r.state === "validated")
                    .map((r) => r.date)
                    .includes(d.toISODate())
        );
    }

    /**
     * @override
     */
    onMultiDelete(selectedCells) {
        const records = this.getSelectedRecords(selectedCells);
        return this.model.unlinkRecords(
            records.filter((r) => r.state !== "validated").map((r) => r.id)
        );
    }

    onMultiReplace(values, selectedCells) {
        const records = this.getSelectedRecords(selectedCells);
        const dates = this.getDatesWithoutValidatedWorkEntry(selectedCells, records);
        return this.model.multiReplaceRecords(
            values,
            dates,
            records.filter((r) => r.state !== "validated")
        );
    }

    onResetWorkEntries(selectedCells) {
        const records = this.getSelectedRecords(selectedCells);
        const dates = this.getDatesWithoutValidatedWorkEntry(selectedCells, records);
        this.model.resetWorkEntries(
            dates,
            records.filter((r) => r.state !== "validated").map((r) => r.id)
        );
    }
}
