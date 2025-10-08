import { WorkEntryCalendarMultiSelectionButtons } from "@hr_work_entry/views/work_entry_calendar/work_entry_multi_selection_buttons";
import { useWorkEntry } from "@hr_work_entry/views/work_entry_hook";
import { useService } from "@web/core/utils/hooks";
import { CalendarController } from "@web/views/calendar/calendar_controller";

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
