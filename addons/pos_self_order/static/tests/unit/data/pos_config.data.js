import { patch } from "@web/core/utils/patch";
import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";
import { MockServer } from "@web/../tests/web_test_helpers";

patch(PosConfig.prototype, {
    _load_pos_self_data_read(records) {
        records[0]._self_ordering_image_background_ids = [];
        records[0]._self_ordering_image_home_ids = [];
        return records;
    },
    _load_self_data_models() {
        return [
            "pos.config",
            "pos.session",
            "pos.preset",
            "resource.calendar.attendance",
            "pos.order",
            "pos.order.line",
            "pos.payment",
            "pos.payment.method",
            "res.partner",
            "res.currency",
            "pos.category",
            "product.template",
            "product.product",
            "product.combo",
            "product.combo.item",
            "res.company",
            "account.tax",
            "account.tax.group",
            "res.country",
            "product.category",
            "product.pricelist",
            "product.pricelist.item",
            "account.fiscal.position",
            "res.lang",
            "product.attribute",
            "product.attribute.custom.value",
            "product.template.attribute.line",
            "product.template.attribute.value",
            "product.tag",
            "decimal.precision",
            "uom.uom",
            "pos.printer",
            "pos_self_order.custom_link",
            "restaurant.floor",
            "restaurant.table",
            "account.cash.rounding",
            "res.country",
            "res.country.state",
            "ir.ui.view",
        ];
    },
    getModelsToLoadSelf() {
        return this._load_self_data_models();
    },
    getModelDependencies(model) {
        return MockServer.env["pos.session"].getModelDependencies(model) || [];
    },
    getModelFieldsToLoadSelf(model) {
        return model._load_pos_self_data_fields
            ? model._load_pos_self_data_fields()
            : MockServer.env["pos.session"].getModelFieldsToLoad(model);
    },
    processPosReadDataSelf(model, records) {
        return model._load_pos_self_data_read
            ? model._load_pos_self_data_read(records)
            : MockServer.env["pos.session"].processPosReadData(model, records);
    },
    load_self_data() {
        const modelToLoad = this.getModelsToLoadSelf();
        const response = modelToLoad.reduce((acc, modelName) => {
            acc[modelName] = {};
            return acc;
        }, {});

        for (const modelName of modelToLoad) {
            const model = MockServer.env[modelName];
            response[modelName].dependencies = this.getModelDependencies(model, {});
            response[modelName].fields = this.getModelFieldsToLoadSelf(model);
            response[modelName].relations = MockServer.env["pos.session"]._load_data_relations(
                modelName,
                response[modelName].fields
            );
            response[modelName].records = this.processPosReadDataSelf(
                model,
                model.search_read([], response[modelName].fields, false, false, false, false)
            );
        }
        return response;
    },
});

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    self_ordering_mode: "kiosk",
}));
