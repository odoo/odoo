import { GraphRenderer } from "@web/views/graph/graph_renderer";

export const LivechatGraphRendererMixin = (model) =>
    class extends GraphRenderer {
        async onGraphClickedFinal(domain) {
            const action = this.env.services.orm.call(
                model,
                "action_open_discuss_channel_view",
                [],
                { domain }
            );
            this.env.services.action.doAction(action);
        }
    };
