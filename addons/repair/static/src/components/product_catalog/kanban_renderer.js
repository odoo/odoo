import { patch } from "@web/core/utils/patch";
import { ProductCatalogKanbanRenderer } from "@product/product_catalog/kanban_renderer";

patch(ProductCatalogKanbanRenderer.prototype, {
    get createProductContext() {
        const context = super.createProductContext;
        if (this.props.list.evalContext.active_model == "repair.service.line") {
            context["default_type"] = "service";
        }
        return context;
    },
});
