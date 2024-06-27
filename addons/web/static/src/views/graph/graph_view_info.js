import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const viewInfoRegistry = registry.category("view_info");

export const graphViewInfo = {
    type: "graph",
    display_name: _t("Graph"),
    icon: "fa fa-area-chart",
    multiRecord: true,
    bundle: "web.assets_backend_lazy",
};

viewInfoRegistry.add("graph", graphViewInfo);
