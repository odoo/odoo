import { LivechatGraphRendererMixin } from "@im_livechat/views/lazy/im_livechat_graph_renderer_mixin";

import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";

registry.category("views").add("im_livechat.channel_report_graph_views", {
    ...graphView,
    Renderer: LivechatGraphRendererMixin("im_livechat.report.channel"),
});
