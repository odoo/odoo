import { registry } from "@web/core/registry";
import { graphViewInfo } from "@web/views/graph/graph_view_info"

export const forecastGraphViewInfo = {
    ...graphViewInfo,
    bundle: "web.assets_backend_lazy",
};

registry.category("view_info").add("forecast_graph", forecastGraphViewInfo);
