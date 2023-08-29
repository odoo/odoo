/** @odoo-module */

import { registry } from "@web/core/registry";

registry
    .category("mock_server")
    .add("res.currency/get_currencies_for_spreadsheet", function (route, args) {
        const currencyNames = args.args[0];
        const result = [];
        for (const currencyName of currencyNames) {
            const curr = this.models["res.currency"].records.find(
                (curr) => curr.name === currencyName
            );

            result.push({
                code: curr.name,
                symbol: curr.symbol,
                decimalPlaces: curr.decimal_places || 2,
                position: curr.position || "after",
            });
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
    });
