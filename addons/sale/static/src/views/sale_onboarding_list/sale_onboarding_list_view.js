import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { SaleListRenderer } from "./sale_onboarding_list_renderer";

export const SaleListView = {
    ...listView,
    Renderer: SaleListRenderer,
};

registry.category("views").add("sale_onboarding_list", SaleListView);
