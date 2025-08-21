import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
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
    static withCache = false;

    async _loadData(params) {
        // if orm have isSample field and its value set to be true then we have sample data as there is no product found for selected vendor, show sample data
        const isSample = this.orm.isSample !== undefined ? this.orm.isSample : false;
        const result = await super._loadData(...arguments);
        if (!params.isMonoRecord) {
            let records;
            if (params.groupBy?.length) {
                // web_read_group: find all opened records from (sub)group
                records = [];
                const stackGroups = [...result.groups];
                while (stackGroups.length) {
                    const group = stackGroups.pop();
                    if (group.groups?.length) {
                        stackGroups.push(...group.groups);
                    }
                    if (group.records?.length) {
                        records.push(...group.records);
                    }
                }
            } else {
                records = result.records;
            }

            let orderLinesInfo;
            if (!isSample) {
                orderLinesInfo = await rpc("/product/catalog/order_lines_info", this._getOrderLinesInfoParams(params, records.map((rec) => rec.id)));
            } else {
                orderLinesInfo = this._getSampleOrderLineInfo();
            }
            for (const record of records) {
                record.productCatalogData = orderLinesInfo[record.id];
            }
        }
        return result;
    }

    _getOrderLinesInfoParams(params, productIds) {
        return {
            order_id: params.context.order_id,
            product_ids: productIds,
            res_model: params.context.product_catalog_order_model,
            child_field: params.context.child_field,
        }
    }

    _getSampleOrderLineInfo() {
         // this function only returns data for sample view similar to rpc call ("/product/catalog/order_lines_info) made in _loadData
        const sampleOrderLineInfo = {};
        const numRecords = 10; // Number of records to generate
        for (let i = 1; i <= numRecords; i++) {
            sampleOrderLineInfo[i] = {
                isSample: true,
                quantity: Math.floor(Math.random() * 10),
                min_qty: 0,
                price: Math.floor(Math.random() * 500) + 100,
                productType: "consu",
                readOnly: false,
                uomDisplayName: _t("Units"),
            };
        }
        return sampleOrderLineInfo;
    }
}
