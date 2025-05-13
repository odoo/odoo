import { registry } from "@web/core/registry";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { pivotView } from "@web/views/pivot/pivot_view";

export class ImLiveChatReportPivotRenderer extends PivotRenderer {
    setup() {
        super.setup();
        this.recordCount = 0;
    }

    openView(domain, views, context, newWindow) {
        if (this.recordCount !== 1) {
            super.openView(domain, views, context, newWindow);
            return;
        }
        this.model.orm
            .search(this.model.metaData.resModel, domain, { limit: 1 })
            .then(([reportId]) => {
                this.actionService.doAction({
                    name: this.model.metaData.title,
                    type: "ir.actions.act_window",
                    res_model: this.model.metaData.resModel,
                    res_id: reportId,
                    views: [[false, "form"]],
                    target: "current",
                    context,
                });
            });
    }

    onOpenView(cell, newWindow) {
        [this.recordCount] = this.model.data.counts[JSON.stringify(cell.groupId)];
        super.onOpenView(cell, newWindow);
    }
}

export const ImLiveChatReportPivotView = {
    ...pivotView,
    Renderer: ImLiveChatReportPivotRenderer,
};

registry.category("views").add("im_livechat.report_channel_pivot_view", ImLiveChatReportPivotView);
