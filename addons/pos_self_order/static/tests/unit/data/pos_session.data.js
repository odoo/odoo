import { patch } from "@web/core/utils/patch";
import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";
import { MockServer } from "@web/../tests/web_test_helpers";

// Loading system of self order is in pos.session in hoot tests. This is
// to avoid code duplication with point_of_sale tests.
patch(PosSession.prototype, {
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
            "pos.printer",
            "res.country",
            "product.category",
            "product.pricelist",
            "product.pricelist.item",
            "pos_self_order.custom_link",
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
            "restaurant.floor",
            "restaurant.table",
            "account.cash.rounding",
            "res.country",
            "res.country.state",
        ];
    },
    getModelsToLoadSelf() {
        return this._load_self_data_models();
    },
    getModelFieldsToLoadSelf(model) {
        return model._load_pos_self_data_fields
            ? model._load_pos_self_data_fields()
            : this.getModelFieldsToLoad(model);
    },
    processPosReadDataSelf(model, records) {
        return model._load_pos_self_data_read
            ? model._load_pos_self_data_read(records)
            : this.processPosReadData(model, records);
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
            response[modelName].relations = this._load_data_relations(
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
