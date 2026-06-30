import { patch } from "@web/core/utils/patch";
import { PosSession } from "@point_of_sale/../tests/unit/data/pos_session.data";

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
    getModelsToLoad(opts) {
        if (opts.self_ordering) {
            return this._load_self_data_models();
        }
        return super.getModelsToLoad(opts);
    },
    getModelFieldsToLoad(model, opts) {
        if (opts.self_ordering && model._load_pos_self_data_fields) {
            return model._load_pos_self_data_fields();
        }
        return super.getModelFieldsToLoad(model, opts);
    },
    processPosReadData(model, records, opts) {
        if (opts.self_ordering && model._load_pos_self_data_read) {
            return model._load_pos_self_data_read(records);
        }
        return super.processPosReadData(model, records, opts);
    },
});
