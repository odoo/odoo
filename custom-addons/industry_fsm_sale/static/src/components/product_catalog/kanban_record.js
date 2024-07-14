/** @odoo-module */

import { useSubEnv } from "@odoo/owl";
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { useService } from '@web/core/utils/hooks';

export class FSMProductCatalogKanbanRecord extends ProductCatalogKanbanRecord {
    setup() {
        super.setup();
        this.orm = useService('orm');
        useSubEnv({
            ...this.env,
            fsm_task_id: this.props.record.context.fsm_task_id,
            resetQuantity: this.debouncedUpdateQuantity.bind(this),
        });
    }

    async _updateQuantity() {
        const { action, price, min_quantity } = await this.rpc("/product/catalog/update_order_line_info", {
            order_id: this.env.orderId,
            product_id: this.env.productId,
            quantity: this.productCatalogData.quantity,
            res_model: this.env.orderResModel,
            task_id: this.env.fsm_task_id,
        });
        if (price) {
            this.productCatalogData.price = parseFloat(price);
        }
        if (min_quantity) {
            this.productCatalogData.minimumQuantityOnProduct = min_quantity;
        }
        if (action && action !== true) {
            const actionContext = {
                'default_product_id': this.props.record.data.id,
            };
            const options = {
                additionalContext: actionContext,
                onClose: async (closeInfo) => {
                    const lines = await this.orm.searchRead(
                        'sale.order.line',
                        [
                            //["order_id", "=", this.env.orderId], need to remove in case there is no order_id yet
                            ["task_id", "=", this.env.fsm_task_id],
                            ["product_id", "=", this.env.productId],
                            ["product_uom_qty", ">", 0],
                        ],
                        ['product_uom_qty']
                    );
                    this.productCatalogData.quantity = lines.reduce((total, line) => total + line.product_uom_qty, 0);
                    this.productCatalogData.tracking = true;
                },
            };
            await this.action.doAction(action, options);
        }
    }
};

