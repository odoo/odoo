/** @odoo-module */

import { registry } from "@web/core/registry";

registry
    .category("mock_server")
    .add("res.currency/get_company_currency_for_spreadsheet", function (route, args) {
        return {
            code: "EUR",
            symbol: "€",
            position: "after",
            decimalPlaces: 2,
        };
    });
