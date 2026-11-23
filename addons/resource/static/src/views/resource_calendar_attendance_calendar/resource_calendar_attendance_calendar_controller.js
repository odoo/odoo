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
    onMultiDelete(selectedCells) {
        const ids = this.getSelectedRecordIds(selectedCells);
        const dates = this.getDates(selectedCells);
        this.model.multiExcludeDates(ids, dates);
    }
}
