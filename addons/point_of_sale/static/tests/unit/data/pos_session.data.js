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
            "res.currency",
            "pos.note",
            "product.tag",
            "ir.ui.view",
            "pos.prep.order",
            "pos.prep.line",
            "pos.snooze",
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
            "access_token",
        ];
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
        return model._load_pos_data_dependencies ? model._load_pos_data_dependencies() : [];
    }

    async processPosReadData(model, records, opts) {
        for (const record of records) {
            if (!record.write_date) {
                record.write_date = "2025-01-01 10:00:00";
            }
        }
        return (model._load_pos_data_read && (await model._load_pos_data_read(records))) || records;
    }

    _load_data_relations(model, fields) {
        const response = {};
        const serverModel = MockServer.env[model];
        const posFields = fields.length ? fields : this.getModelFieldsToLoad(serverModel, {});
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

    async load_data(session_id, local_data = {}) {
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
            response[modelName].records = await this.processPosReadData(
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
        return data;
    }

    filter_local_data() {
        return {};
    }

    get_cash_in_out_list() {
        return [];
    }

    get_closing_control_data() {
        const orders = this.env["pos.order"]
            .search_read([], ["id", "amount_total", "payment_ids"])
            .filter((o) => o.state === "paid" || o.state === "done");
        const totalAmount = orders.reduce((sum, o) => sum + (o.amount_total || 0), 0);
        const cashPayments = this.env["pos.payment"]
            .search_read([], ["amount", "payment_method_id"])
            .filter((p) => {
                const pm = this.env["pos.payment.method"].search_read(
                    [["id", "=", p.payment_method_id]],
                    ["type"]
                )[0];
                return pm && pm.type === "cash";
            });
        const totalCash = cashPayments.reduce((sum, p) => sum + (p.amount || 0), 0);
        return {
            orders_details: { quantity: orders.length, amount: totalAmount },
            opening_notes: "",
            default_cash_details: {
                id: 1,
                name: "Cash",
                amount: totalCash,
                opening: 0,
                payment_amount: totalCash,
                moves: [],
            },
            non_cash_payment_methods: [],
            is_manager: false,
            amount_authorized_diff: null,
        };
    }

    get_order_count_by_preset() {
        return [];
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
            state: "opened",
            access_token: "e09c4843-c913-463a-959d-b9e235881201",
            write_date: "2025-01-01 10:00:00",
        },
    ];
}
