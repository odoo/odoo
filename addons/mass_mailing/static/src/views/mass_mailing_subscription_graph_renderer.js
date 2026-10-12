import { registry } from "@web/core/registry";
import { GraphRenderer } from "@web/views/graph/graph_renderer";
import { graphView } from "@web/views/graph/graph_view";


export class SubscriptionGraphRenderer extends GraphRenderer {
    /**
     * Open the pivot view instead of the list view on graph click.
     * @override
     */
    openView(domain, views, context) {
        this.actionService.doAction(
            {
                context,
                domain,
                name: this.model.metaData.title,
                res_model: this.model.metaData.resModel,
                target: "current",
                type: "ir.actions.act_window",
                views: [[false, "pivot"], [false, "form"]],
            },
            {
                viewType: "pivot",
            }
        );
    }
}

export const subscriptionGraphView = {
    ...graphView,
    Renderer: SubscriptionGraphRenderer,
};

registry.category("views").add("subscription_graph", subscriptionGraphView);
