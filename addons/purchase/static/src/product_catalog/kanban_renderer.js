import { useService } from "@web/core/utils/hooks";

import { ProductCatalogKanbanRenderer } from "@product/product_catalog/kanban_renderer";

export class PurchaseProductCatalogKanbanRenderer extends ProductCatalogKanbanRenderer {
    static template = "PurchaseProductCatalogKanbanRenderer";

    setup() {
        super.setup();
        this.action = useService("action");
    }

    get createProductContext() {
        return {default_seller_ids: [{partner_id:this.props.list._config.context.partner_id}],};
    }

    async createProduct() {
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "product.product",
                target: "new",
                views: [[false, "form"]],
                view_mode: "form",
                context: this.createProductContext,
            },
            {
                props: {
                    onSave: async (record, params) => {
                        await this.props.list.model.load();
                        this.props.list.model.useSampleModel = false;
                        this.action.doAction({
                            type: "ir.actions.act_window_close",
                        });
                    },
                }
            }
        );
    }
}
