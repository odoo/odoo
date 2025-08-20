import { CalendarController } from "@web/views/calendar/calendar_controller";
import { useMultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";
import { CallbackRecorder } from "@web/search/action_hook";
import { useBus } from "@web/core/utils/hooks";
import { WorkEntryCalendarMultiSelectionButtons } from "@hr_work_entry/views/work_entry_calendar/work_entry_multi_selection_buttons";
import { onWillRender } from "@odoo/owl";
import { user } from "@web/core/user";
import { useWorkEntry } from "@hr_work_entry/views/work_entry_hook";
const { DateTime } = luxon;

export class WorkEntryCalendarController extends CalendarController {
    static components = {
        ...CalendarController.components,
        MultiSelectionButtons: WorkEntryCalendarMultiSelectionButtons,
    };

    setup() {
        super.setup(...arguments);
        const { onRegenerateWorkEntries } = useWorkEntry({
            getEmployeeIds: this.getEmployeeIds.bind(this),
            getRange: this.model.computeRange.bind(this.model),
            onClose: this.model.load.bind(this.model),
        });
        this.onRegenerateWorkEntries = onRegenerateWorkEntries;

        onWillRender(async () => {
            const userFavoritesWorkEntriesIds = await this.orm.formattedReadGroup(
                "hr.work.entry",
                [
                    ["create_uid", "=", user.userId],
                    ["create_date", ">", DateTime.local().minus({ months: 3 }).toISODate()],
                ],
                ["work_entry_type_id", "create_date:day"],
                [],
                {
                    order: "create_date:day desc",
                    limit: 6,
                }
            );
            this.userFavoritesWorkEntries = await this.orm.read(
                "hr.work.entry.type",
                userFavoritesWorkEntriesIds.map((r) => r.work_entry_type_id[0]),
                ["display_name", "display_code", "color"]
            );
            this.userFavoritesWorkEntries = this.userFavoritesWorkEntries.sort((a, b) =>
                a.display_code
                    ? a.display_code.localeCompare(b.display_code)
                    : a.display_name.localeCompare(b.display_name)
            );
        });
    }

    async splitRecord(record) {
        const split_work_entry_id = await this.orm.call("hr.work.entry", "action_split", [
            record.id,
        ]);
        if (split_work_entry_id) {
            await this.editRecord({ ...record, id: split_work_entry_id });
        }
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
    prepareSelectionFeature() {
        this.selectedCells = null;
        this.multiSelectionButtonsReactive = useMultiSelectionButtons({
            onCancel: this.cleanSquareSelection.bind(this),
            onAdd: (multiCreateData) => {
                this.onMultiCreate(multiCreateData, this.selectedCells);
                this.cleanSquareSelection();
            },
            onDelete: () => {
                this.onMultiDelete(this.selectedCells);
                this.cleanSquareSelection();
            },
            nbSelected: 0,
            multiCreateView: this.model.meta.multiCreateView,
            resModel: this.model.meta.resModel,
            multiCreateValues: this.props.state?.multiCreateValues,
            showMultiCreateTimeRange: this.model.showMultiCreateTimeRange,
            context: this.props.context,
        });

        this.callbackRecorder = new CallbackRecorder();
        this._baseRendererProps.callbackRecorder = this.callbackRecorder;
        this._baseRendererProps.onSquareSelection = (selectedCells) =>
            this.updateMultiSelection(selectedCells);
        this._baseRendererProps.cleanSquareSelection = this.cleanSquareSelection.bind(this);

        useBus(this.model.bus, "update", this.cleanSquareSelection.bind(this));
    }

    updateMultiSelection(selectedCells) {
        this.selectedCells = selectedCells;
        this.multiSelectionButtonsReactive.visible = true;
        this.multiSelectionButtonsReactive.userFavoritesWorkEntries = this.userFavoritesWorkEntries;
        this.multiSelectionButtonsReactive.nbSelected = this.getSelectedRecordIds(
            this.selectedCells
        ).length;
        this.multiSelectionButtonsReactive.selection = this.getSelectedRecords(this.selectedCells);
        this.multiSelectionButtonsReactive.onQuickReplace = (multiCreateData) => {
            this.onMultiReplace(multiCreateData, this.selectedCells);
        };
        this.multiSelectionButtonsReactive.onQuickReset = () => {
            this.onResetWorkEntries(this.selectedCells);
        };
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

    onMultiReplace(multiCreateData, selectedCells) {
        const records = this.getSelectedRecords(selectedCells);
        const dates = this.getDatesWithoutValidatedWorkEntry(selectedCells, records);
        return this.model.multiReplaceRecords(
            multiCreateData,
            dates,
            records.filter((r) => r.state !== "validated").map((r) => r.id)
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
