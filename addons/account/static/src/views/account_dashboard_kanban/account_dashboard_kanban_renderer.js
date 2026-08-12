import { proxy } from "@odoo/owl";
import { useSubEnv } from "@web/owl2/utils";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { AccountDashboardKpis } from "@account/components/account_dashboard_kpis/account_dashboard_kpis";
import { DashboardKanbanRecord } from "./account_dashboard_kanban_record";


export class DashboardKanbanRenderer extends KanbanRenderer {
    static template = "account.DashboardKanbanRenderer";
    static components = {
        ...KanbanRenderer.components,
        KanbanRecord: DashboardKanbanRecord,
        AccountDashboardKpis,
    };

    setup() {
        super.setup();
        useSubEnv({
            dashboardState: proxy({isDragging: false}),
            setDragging: this.setDragging.bind(this),
        });
    }

    get coaState() {
        const first = this.props.list.records[0];
        if (first) {
            const dashboard = JSON.parse(first.data.kanban_dashboard);
            return {
                showBanner: dashboard.show_coa_banner,
                coaName: dashboard.coa_name,
            };
        }
        return { showBanner: false, coaName: "" };
    }

    async reloadCoa() {
        const first = this.props.list.records[0];
        if (first) {
            await first.model.orm.call("account.journal", "action_reload_coa", [[first.resId]]);
            await this.props.list.load();
        }
    }

    kanbanDragEnter(e) {
        this.setDragging(e.dataTransfer.types.includes("Files"));
    }

    kanbanDragLeave(e) {
        const mouseX = e.clientX, mouseY = e.clientY;
        const {x, y, width, height} = this.rootRef().getBoundingClientRect();
        const mouseInsideKanbanRenderer = mouseX > x && mouseX <= x + width && mouseY > y && mouseY <= y + height;
        if (!mouseInsideKanbanRenderer || !e.dataTransfer.types.includes("Files")) {
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
