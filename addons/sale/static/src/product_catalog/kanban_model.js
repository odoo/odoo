import { ProductCatalogKanbanModel } from "@product/product_catalog/kanban_model";

export class SaleProductCatalogKanbanModel extends ProductCatalogKanbanModel {

    async _loadData(params) {
        const orignal_limit = params.limit || this.initialLimit;
        const orignal_offset = params.offset || 0;
        const new_limit = await this.orm.searchCount(params.resModel, params.domain);
        params.limit = new_limit;
        params.offset = 0;
        const result = await super._loadData(...arguments);

        if (!params.isMonoRecord && !params.groupBy.length) {
            if (result.records.some(record => 'last_invoice_date' in record.productCatalogData)) {
                const prioritized_products = result.records.filter(obj => obj.productCatalogData.last_invoice_date != false)
                const remaining_products = result.records.filter(obj => obj.productCatalogData.last_invoice_date == false)
                result.records = prioritized_products.sort((obj1, obj2) => {
                    return new Date(obj2.productCatalogData.last_invoice_date || 0) - new Date(obj1.productCatalogData.last_invoice_date || 0);
                });
                result.records.push(...remaining_products);
            }
        }
        result.records = result.records.slice(orignal_offset, orignal_limit + orignal_offset);
        params.limit = orignal_limit;
        params.offset = orignal_offset;
        return result;
    }
}
