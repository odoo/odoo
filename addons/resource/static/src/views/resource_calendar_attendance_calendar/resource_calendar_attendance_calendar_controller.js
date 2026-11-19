import { CalendarController } from "@web/views/calendar/calendar_controller";
import { ResourceMultiSelectionButtons } from "@resource/views/view_components/resource_multi_selection_buttons";

export class ResourceCalendarAttendanceCalendarController extends CalendarController {
    static components = {
        ...CalendarController.components,
        MultiSelectionButtons: ResourceMultiSelectionButtons,
    };

    /**
     * @override
     */
    prepareMultiSelectionButtonsReactive() {
        const reactive = super.prepareMultiSelectionButtonsReactive();
        reactive.onQuickAdd = (block) => {
            this.onQuickAdd(block, this.selectedCells);
            this.cleanSquareSelection();
        };
        reactive.quickAddBlocks = [];
        return reactive;
    }

    /**
     * @override
     */
    updateMultiSelection(selectedCells) {
        super.updateMultiSelection(...arguments);
        this.multiSelectionButtonsReactive.quickAddBlocks = this.model.getQuickAddBlocks(
            this.getDates(selectedCells)
        );
    }

    onQuickAdd(block, selectedCells) {
        return this.model.quickAddRecords(block, this.getDates(selectedCells));
    }

    /**
     * @override
     */
    onMultiDelete(selectedCells) {
        const ids = this.getSelectedRecordIds(selectedCells);
        const dates = this.getDates(selectedCells);
        this.model.multiExcludeDates(ids, dates);
    }
}
