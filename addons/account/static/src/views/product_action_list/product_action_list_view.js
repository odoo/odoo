import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ProductActionListRenderer } from "./product_action_list_renderer";

registry.category("views").add("product_sellable_action_list", {
    ...listView,
    Renderer: ProductActionListRenderer,
});
