import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { DashboardKanbanRecord } from "./account_dashboard_kanban_record";

import { useSubEnv, reactive } from "@odoo/owl";

export class DashboardKanbanRenderer extends KanbanRenderer {
    static template = "account.DashboardKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: DashboardKanbanRecord,
    };

    setup() {
        super.setup();
        useSubEnv({
            dashboardState: reactive({isDragging: false}),
            setDragging: this.setDragging.bind(this),
        });
    }

    kanbanDragEnter(e) {
        this.env.dashboardState.isDragging = true;
    }

    kanbanDragLeave(e) {
        const mouseX = e.clientX, mouseY = e.clientY;
        const {x, y, width, height} = this.rootRef.el.getBoundingClientRect();
        if (!(mouseX > x && mouseX <= x + width && mouseY > y && mouseY <= y + height)) {
            // if the mouse position is outside the kanban renderer, all cards should hide their dropzones.
            this.setDragging(false);
        } else {
            this.setDragging(true);
        }
    }

    kanbanDragDrop(e) {
        this.setDragging(false);
        return false;
    }

    setDragging(value) {
        this.env.dashboardState.isDragging = value;
    }
}
