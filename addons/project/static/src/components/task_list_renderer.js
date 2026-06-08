import { onPatched } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ListRenderer } from "@web/views/list/list_renderer";

export class TaskListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        onPatched(() => {
            this.focusName(this.editedRecord());
        });
    }

    focusName(editedRecord) {
        if (editedRecord?.isNew && !editedRecord.dirty) {
            const col = this.columns.find((c) => c.name === "name");
            this.focusCell(col);
        }
    }
}
