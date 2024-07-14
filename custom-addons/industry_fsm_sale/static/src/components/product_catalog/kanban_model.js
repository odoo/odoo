/** @odoo-module */

import { Record } from "@web/model/relational_model/record";
import { RelationalModel } from "@web/model/relational_model/relational_model";

class ProductCatalogRecord extends Record {
    setup(config, data, options = {}) {
        this.productCatalogData = data.productCatalogData;
        data = { ...data };
        delete data.productCatalogData;
        super.setup(config, data, options);
    }
}

export class FSMProductCatalogKanbanModel extends RelationalModel {
    static Record = ProductCatalogRecord;

    async _loadData(params) {
        const result = await super._loadData(...arguments);
        if (!params.isMonoRecord && !params.groupBy.length) {
            const saleOrderLinesInfo = await this.rpc("/product/catalog/order_lines_info", {
                order_id: params.context.order_id,
                product_ids: result.records.map((rec) => rec.id),
                task_id: params.context.fsm_task_id,
                res_model: params.context.product_catalog_order_model,
            });
            for (const record of result.records) {
                record.productCatalogData = saleOrderLinesInfo[record.id];
            }
        }
        return result;
    }
}
