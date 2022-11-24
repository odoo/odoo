/** @odoo-module */
import { KanbanModel, KanbanDynamicRecordList } from "@web/views/kanban/kanban_model";

export class ProductCatalogKanbanDynamicRecordList extends KanbanDynamicRecordList {

    async load(params = {}) {
        await super.load(...arguments);
        await this._loadCatalogData();
    }

    async _loadCatalogData() {
        const saleOrderLinesInfo = await this.model.rpc("/sales/catalog/sale_order_lines_info", {
            order_id: this.context.order_id,
            product_ids: this.records.map((rec) => rec.resId),
        });

        for (const record of this.records) {
            record.productCatalogData = saleOrderLinesInfo[record.resId];
        }
    }
}

export class ProductCatalogKanbanModel extends KanbanModel {}

ProductCatalogKanbanModel.DynamicRecordList = ProductCatalogKanbanDynamicRecordList;
