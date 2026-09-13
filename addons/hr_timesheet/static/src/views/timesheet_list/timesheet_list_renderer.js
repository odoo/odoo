import { ListRenderer } from "@web/views/list/list_renderer";

export class TimesheetListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.multiEditLimitedFields = ["task_id"];
        this.multiEditBlackList = ["project_id"];
        this.lastLength = 0;
    }

    isCellReadonly(column, record) {
        const isCellReadonly = super.isCellReadonly(column, record);
        const selected = this.props.list.selection;
        if (isCellReadonly) {
            return isCellReadonly;
        } else if (selected.length <= 1) {
            // If only one element is selected multi-select readonly should not apply
            this.lastLength = 1;
            return false;
        } else if (this.multiEditBlackList.includes(column.name)) {
            return true;
        } else if (this.multiEditLimitedFields.includes(column.name)) {
            //If there is a difference between lastLength and selected.length, then there must be a change in the selection
            if (this.lastLength !== selected.length) {
                this.lastLength = selected.length;
                this.allowTasks = selected.every(
                    (line) => line.data.project_id.id === selected[0].data.project_id.id
                );
            }
            return !this.allowTasks;
        }
    }
}
