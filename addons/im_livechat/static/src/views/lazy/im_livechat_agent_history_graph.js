import { LivechatGraphRendererMixin } from "@im_livechat/views/lazy/im_livechat_graph_renderer_mixin";

import { registry } from "@web/core/registry";
import { graphView } from "@web/views/graph/graph_view";

registry.category("views").add("im_livechat.agent_history_graph", {
    ...graphView,
    Renderer: LivechatGraphRendererMixin("im_livechat.channel.member.history"),
});
