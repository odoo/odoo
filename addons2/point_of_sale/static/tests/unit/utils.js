/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("mock_server").add("pos.session/load_pos_data", async function (route, args) {
    return {
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
        },
        "res.users": {
            id: 2,
            name: "Mitchell Admin",
            role: "manager",
        },
        "account.fiscal.position": [],
    };
});

registry
    .category("mock_server")
    .add("pos.session/get_pos_ui_product_product_by_params", async function (route, { args }) {
        return this.mockSearchRead("product.product", args[1], {});
    });

// Used to load the default UOM. Seems like this should be doe in load_pos_data?
registry
    .category("mock_server")
    .add("ir.model.data/check_object_reference", async function (route, { args: [model, xmlId] }) {
        if (model !== "uom" || xmlId !== "product_uom_unit") {
            throw new Error(`Unknown object reference: ${model}.${xmlId}`);
        }
        return ["uom", 1];
    });

// FIXME POSREF missing unhandledrejection handler and other code form qunit.js
