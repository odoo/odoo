import { MultiSelectionButtons } from "@web/views/view_components/multi_selection_buttons";

export class ResourceMultiSelectionButtons extends MultiSelectionButtons {
    /**
     * @override
     */
    computeValues(record) {
        const values = super.computeValues(...arguments);
        if (values.recurrency_end_type !== "date") {
            delete values.recurrency_until;
        }
        return values;
    }
}
