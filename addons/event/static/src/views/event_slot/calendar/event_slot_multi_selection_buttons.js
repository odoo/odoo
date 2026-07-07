import { MultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";
import { useService } from "@web/core/utils/hooks";

export class EventSlotCalendarMultiSelectionButtons extends MultiSelectionButtons {
    // Add a hint to ensure users understand they need to click on a date to add slots.
    static template = "event.EventSlotCalendarMultiSelectionButtons";

    setup() {
        this.uiService = useService("ui");
    }
};
