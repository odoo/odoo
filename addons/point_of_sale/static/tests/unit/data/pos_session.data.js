import { MockServer, models } from "@web/../tests/web_test_helpers";

export class PosSession extends models.ServerModel {
    _name = "pos.session";
    _orderRef = 1;

    _load_pos_data_models(config_id) {
        return [
            "pos.session",
            "pos.config",
            "pos.preset",
            "resource.calendar.attendance",
            "pos.order",
            "pos.order.line",
            "pos.pack.operation.lot",
            "pos.payment",
            "pos.payment.method",
            "pos.printer",
            "pos.category",
            "pos.bill",
            "res.company",
            "account.tax",
            "account.tax.group",
            "product.template",
            "product.product",
            "product.attribute",
            "product.attribute.custom.value",
            "product.template.attribute.line",
            "product.template.attribute.value",
            "product.combo",
            "product.combo.item",
            "res.users",
            "res.partner",
            "product.uom",
            "decimal.precision",
            "uom.uom",
            "res.country",
            "res.country.state",
            "res.lang",
            "product.category",
            "product.pricelist",
            "product.pricelist.item",
            "account.cash.rounding",
            "account.fiscal.position",
            "stock.picking.type",
            "res.currency",
            "pos.note",
            "product.tag",
        ];
    }

    _load_pos_data_fields() {
        return [
            "id",
            "name",
            "user_id",
            "config_id",
            "start_at",
            "stop_at",
            "payment_method_ids",
            "state",
            "update_stock_at_closing",
            "cash_register_balance_start",
            "access_token",
        ];
    }

    _load_pos_data_dependencies() {
        return [];
    }

    // These methods are designed to be overridden to customize the POS data loading behavior using the provided `opts`.
    getModelsToLoad(opts) {
        return this._load_pos_data_models();
    }

    getModelFieldsToLoad(model, opts) {
        const fields = model._load_pos_data_fields();
        if (fields.length > 0) {
            if (!fields.includes("id")) {
                fields.push("id");
            }

            if (!fields.includes("write_date")) {
                fields.push("write_date");
            }
        }
        return fields;
    }

    getModelDependencies(model) {
        return model._load_pos_data_dependencies();
    }

    processPosReadData(model, records, opts) {
        return (model._load_pos_data_read && model._load_pos_data_read(records)) || records;
    }

    _load_data_relations(model, fields) {
        const response = {};
        const serverModel = MockServer.env[model];
        const posFields = this.getModelFieldsToLoad(serverModel, {});
        const allFields = serverModel.fields_get();
        const base = posFields.length ? posFields : Object.keys(allFields);

        if (!base.includes("id")) {
            base.push("id");
        }

        if (!base.includes("write_date")) {
            base.push("write_date");
        }

        for (const fieldName of base) {
            const field = allFields[fieldName];

            if (!field) {
                console.debug(`Field ${fieldName} not found in model ${model}`);
                continue;
            }

            response[fieldName] = {
                name: fieldName,
                model: model,
                compute: Boolean(field.compute),
                related: Boolean(field.related),
                type: field.type,
                relation: field.relation,
                inverse_name: field.inverse_fname_by_model_name?.[field.relation] || false,
            };
        }

        return response;
    }

    load_data(session_id, local_data = {}) {
        const modelToLoad =
            local_data.models && local_data.models.length
                ? local_data.models
                : this.getModelsToLoad(local_data);
        const response = modelToLoad.reduce((acc, modelName) => {
            acc[modelName] = {};
            return acc;
        }, {});

        for (const modelName of modelToLoad) {
            const model = MockServer.env[modelName];
            response[modelName].dependencies = this.getModelDependencies(model, local_data);
            response[modelName].fields = this.getModelFieldsToLoad(model, {});
            response[modelName].relations = this._load_data_relations(
                modelName,
                response[modelName].fields
            );
            response[modelName].records = this.processPosReadData(
                model,
                model.search_read([], response[modelName].fields, false, false, false, false),
                false
            );
        }
        if (local_data.only_records) {
            return Object.fromEntries(
                Object.entries(response).map(([model, value]) => [model, value.records])
            );
        }
        return response;
    }

    _load_pos_data_read(data) {
        data[0]["_partner_commercial_fields"] = [];
        data[0]["_server_version"] = "18.3+e";
        data[0]["_base_url"] = "http://localhost:4444";
        data[0]["_data_server_date"] = "2025-07-03 12:40:15";
        data[0]["_has_cash_move_perm"] = true;
        data[0]["_has_available_products"] = true;
        data[0]["_pos_special_products_ids"] = [];
        return data;
    }

    filter_local_data() {
        return {};
    }

    _records = [
        {
            id: 1,
            name: "/",
            user_id: 2,
            config_id: 1,
            start_at: false,
            stop_at: false,
            payment_method_ids: [2, 1],
            state: "opening_control",
            update_stock_at_closing: false,
            cash_register_balance_start: 0.0,
            access_token: "e09c4843-c913-463a-959d-b9e235881201",
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
