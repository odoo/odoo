import { registry } from "@web/core/registry";
import { PivotRenderer } from "@web/views/pivot/pivot_renderer";
import { pivotView } from "@web/views/pivot/pivot_view";

export class ImLiveChatReportPivotRenderer extends PivotRenderer {
    static template = "im_livechat.ReportPivotRenderer";

    setup() {
        super.setup();
        this.recordCount = 0;
    }

    openView(domain, views, context, newWindow) {
        if (this.recordCount === 1) {
            this.model.orm
                .call(this.model.metaData.resModel, "search", [domain], {
                    limit: 1,
                })
                .then((resIds) => {
                    this.actionService.doAction({
                        name: this.model.metaData.title,
                        type: "ir.actions.act_window",
                        res_model: this.model.metaData.resModel,
                        res_id: resIds[0],
                        views: [[false, "form"]],
                        target: "current",
                        context,
                    });
                })
                .catch(() => {
                    super.openView(domain, views, context, newWindow);
                });
        } else {
            super.openView(domain, views, context, newWindow);
        }
    }

    onOpenView(cell, newWindow, recordCount) {
        this.recordCount = recordCount;
        super.onOpenView(cell, newWindow);
    }
}

export const ImLiveChatReportPivotView = {
    ...pivotView,
    Renderer: ImLiveChatReportPivotRenderer,
};

registry.category("views").add("im_livechat.report_channel_pivot_view", ImLiveChatReportPivotView);
