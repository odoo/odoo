import { registry } from "@web/core/registry";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";

class ImLivechatChannelReportGraphRenderer extends GraphRenderer {
    async onGraphClickedFinal(domain) {
        const action = this.env.services.orm.call(
            "im_livechat.report.channel",
            "action_open_discuss_channel_list_view",
            [],
            { report_channels_domain: domain }
        );
        this.env.services.action.doAction(action);
    }
}

registry.category("views").add("im_livechat.channel_report_graph_views", {
    ...graphView,
    Renderer: ImLivechatChannelReportGraphRenderer,
});
