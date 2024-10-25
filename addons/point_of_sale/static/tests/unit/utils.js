/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("mock_server").add("pos.session/load_data", async function (route, args) {
    return {
<<<<<<< saas-17.2
        custom: {
            server_version: "0.0.0",
            base_url: "http://localhost:8069",
            has_cash_move_perm: true,
            has_available_products: true,
            pos_special_products_ids: [],
||||||| e9d6920bfa66a9cff6a98e3e8f3cccab7e0ea599
        "res.company": { id: 1 },
        "pos.session": { id: 1 },
        "pos.printer": [],
        "pos.config": { id: 1, uuid: "TEST-UUID", trusted_config_ids: [] },
        "res.partner": [...(this.models["res.partner"]?.records || [])],
        "pos.category": [...(this.models["pos.category"]?.records || [])],
        "product.product": [...(this.models["product.product"]?.records || [])],
        "pos.combo": [...(this.models["pos.combo"]?.records || [])],
        "pos.combo.line": [...(this.models["pos.combo.line"]?.records || [])],
        "product.pricelist": [...(this.models["product.pricelist"]?.records || [])],
        "pos.payment.method": [...(this.models["pos.payment.method"]?.records || [])],
        attributes_by_ptal_id: {},
        "res.currency": {
            id: 1,
            name: "USD",
            symbol: "$",
            position: "before",
            rounding: 0.01,
            rate: 1.0,
            decimal_places: 2,
=======
        "res.company": {
            id: 1,
            account_fiscal_country_id: {
                id: 1,
                name: "United States of America",
                code: "US",
            },
        },
        "pos.session": { id: 1 },
        "pos.printer": [],
        "pos.config": { id: 1, uuid: "TEST-UUID", trusted_config_ids: [] },
        "res.partner": [...(this.models["res.partner"]?.records || [])],
        "pos.category": [...(this.models["pos.category"]?.records || [])],
        "product.product": [...(this.models["product.product"]?.records || [])],
        "pos.combo": [...(this.models["pos.combo"]?.records || [])],
        "pos.combo.line": [...(this.models["pos.combo.line"]?.records || [])],
        "product.pricelist": [...(this.models["product.pricelist"]?.records || [])],
        "pos.payment.method": [...(this.models["pos.payment.method"]?.records || [])],
        attributes_by_ptal_id: {},
        "res.currency": {
            id: 1,
            name: "USD",
            symbol: "$",
            position: "before",
            rounding: 0.01,
            rate: 1.0,
            decimal_places: 2,
>>>>>>> 2fb619826c179612976871d40c5e4b059927ee99
        },
        data: Object.entries(this.models).reduce((acc, [model, data]) => {
            acc[model] = data.records;
            return acc;
        }, {}),
        relations: Object.entries(this.models).reduce((acc, [model, data]) => {
            acc[model] = Object.entries(data.fields).reduce((acc, [field, value]) => {
                acc[field] = value;
                return acc;
            }, {});
            return acc;
        }, {}),
        fields: Object.entries(this.models).reduce((acc, [model, data]) => {
            acc[model] = Object.keys(data.fields);
            return acc;
        }, {}),
    };
});

registry
    .category("mock_server")
    .add("pos.session/get_pos_ui_product_product_by_params", async function (route, { args }) {
        return this.mockSearchRead("product.product", args[1], {});
    });

// Used to load the default UOM. Seems like this should be doe in load_data?
registry
    .category("mock_server")
    .add("ir.model.data/check_object_reference", async function (route, { args: [model, xmlId] }) {
        if (model !== "uom" || xmlId !== "product_uom_unit") {
            throw new Error(`Unknown object reference: ${model}.${xmlId}`);
        }
        return ["uom", 1];
    });

// FIXME POSREF missing unhandledrejection handler and other code form qunit.js
