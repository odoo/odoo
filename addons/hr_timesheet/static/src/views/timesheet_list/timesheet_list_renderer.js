
import { ListRenderer } from "@web/views/list/list_renderer";

export class TimesheetListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.multiEditLimitedFields = ["task_id"];
        this.multiEditBlackList = ["project_id"];
        this.lastLength = 0;
    }
    isCellReadonly(column, record) {
        const selected = this.props.list.selection;
        if (selected.length <= 1) {
            this.lastLength = 0;
            return super.isCellReadonly(column, record);
        }
        if (this.multiEditBlackList.includes(column.name)) {
            return true;
        }
        if (this.multiEditLimitedFields.includes(column.name)) {
            if (this.lastLength != selected.length) {
                this.lastLength = selected.length;
                this.allowTasks = selected.every(
                    (line) => line.data.project_id.id === selected[0].data.project_id.id
                );
            }
            return !this.allowTasks;
        }
        return false;
    }
}
