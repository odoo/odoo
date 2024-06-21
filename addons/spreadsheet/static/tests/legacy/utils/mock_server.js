/** @odoo-module */

import { registry } from "@web/core/registry";

registry
    .category("mock_server")
    .add("spreadsheet.mixin/get_display_names_for_spreadsheet", function (route, { args }) {
        const result = [];
        for (const { model, id } of args[0]) {
            const record = this.models[model].records.find((record) => record.id === id);
            result.push(record?.display_name ?? null);
        }
        return result;
    })
    .add("res.currency/get_company_currency_for_spreadsheet", function (route, args) {
        return {
            code: "EUR",
            symbol: "€",
            position: "after",
            decimalPlaces: 2,
        };
    })
    .add("ir.model/display_name_for", function (route, args) {
        const models = args.args[0];
        const records = this.models["ir.model"].records.filter((record) =>
            models.includes(record.model)
        );
        return records.map((record) => ({
            model: record.model,
            display_name: record.name,
        }));
    });
