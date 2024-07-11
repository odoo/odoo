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

export class ProductCatalogKanbanModel extends RelationalModel {
    static Record = ProductCatalogRecord;

    async _loadData(params) {
        const result = await super._loadData(...arguments);
        if (!params.isMonoRecord && !params.groupBy.length) {
            const orderLinesInfo = await this.rpc("/product/catalog/order_lines_info", {
                order_id: params.context.order_id,
                product_ids: result.records.map((rec) => rec.id),
                res_model: params.context.product_catalog_order_model,
            });
            for (const record of result.records) {
                record.productCatalogData = orderLinesInfo[record.id];
            }
        }
        return result;
    }
}
