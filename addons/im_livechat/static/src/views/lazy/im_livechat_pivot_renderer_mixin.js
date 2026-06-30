import { PivotRenderer } from "@web/views/pivot/pivot_renderer";

export const LivechatPivotRendererMixin = (model) =>
    class extends PivotRenderer {
        async openView(domain) {
            const action = this.env.services.orm.call(
                model,
                "action_open_discuss_channel_view",
                [],
                { domain }
            );
            this.env.services.action.doAction(action);
        }
    };
