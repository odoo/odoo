/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRef } from "@odoo/owl";

export class HrFleetKanbanController extends KanbanController {
    setup() {
        super.setup(...arguments);
        this.uploadFileInput = useRef("uploadFileInput");
        this.uploadService = useService("file_upload");
        useBus(
            this.uploadService.bus,
            "FILE_UPLOAD_LOADED",
            () => {
                this.model.load();
            },
        );
    }

    get canCreate() {
        return false;
    }

    async onInputChange(ev) {
        if (!ev.target.files) {
            return;
        }
        this.uploadService.upload(
            "/web/binary/upload_attachment",
            ev.target.files,
            {
                buildFormData: (formData) => {
                    formData.append("model", "fleet.vehicle.assignation.log");
                    formData.append("id", this.props.context.active_id);
                },
            },
        );
        ev.target.value = "";
    }
}
