/** @odoo-module */

import { RelationalModel } from "@web/model/relational_model/relational_model";

export class ProductCatalogKanbanModel extends RelationalModel {
    async load() {
        await super.load(...arguments);

        const saleOrderLinesInfo = await this.rpc("/sales/catalog/sale_order_lines_info", {
            order_id: this.config.context.order_id,
            product_ids: this.root.records.map((rec) => rec.resId),
        });
        for (const record of this.root.records) {
            record.productCatalogData = saleOrderLinesInfo[record.resId];
        }
    }
}
