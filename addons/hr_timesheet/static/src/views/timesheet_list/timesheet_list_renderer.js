import { ListRenderer } from "@web/views/list/list_renderer";
import { getRawValue } from "@web/views/kanban/kanban_record";
export class TimesheetListRenderer extends ListRenderer {
    setup() {
        super.setup();
        // fields editable in multi-edit only if all selected timesheets share the same project
        this.multiEditLimitedFields = ["task_id"];
        // fields never editable in multi-edit
        this.multiEditBlackList = ["project_id"];
    }
    get selectionInfo() {
        if (this._selectionInfo === undefined) {
            const selection = this.props.list.selection;
            const projectId = selection.length && getRawValue(selection[0], "project_id");
            this._selectionInfo = {
                count: selection.length,
                sameProject: selection.every(
                    (timesheet) => getRawValue(timesheet, "project_id") === projectId
                ),
            };
           Promise.resolve().then(() => {
                delete this._selectionInfo;
            });
        }
        return this._selectionInfo;
    }

    isFieldReadonly(column, record) {
        let readonly = super.isFieldReadonly(column, record);
        if (!readonly && record.selected && this.props.list.model.multiEdit) {
            if (this.multiEditBlackList.includes(column.name)) {
                readonly = this.selectionInfo.count > 1;
            } else if (this.multiEditLimitedFields.includes(column.name)) {
                readonly = !this.selectionInfo.sameProject;
            }
        }
        return readonly;
    }
}
