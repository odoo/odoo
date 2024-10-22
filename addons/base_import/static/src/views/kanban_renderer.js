import { patch } from "@web/core/utils/patch";
import { useImportRecordsDropzone } from "@base_import/import_records_dropzone/import_records_dropzone_hook";
import { useService } from "@web/core/utils/hooks";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

patch(KanbanRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.props.archInfo?.canImportRecords) {
            const actionService = useService("action");
            const { context, resModel } = this.props.list.model.config;
            useImportRecordsDropzone(this.rootRef, resModel, async file => {
                await actionService.doAction({
                    type: "ir.actions.client",
                    tag: "import",
                    params: { model: resModel, context, file },
                });
            });
        }
    }
});
