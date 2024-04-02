/** @odoo-module */

import { registry } from "@web/core/registry";

registry.category("mock_server").add("pos.session/load_data", async function (route, args) {
    const mockData = {};
    const relations = Object.entries(this.models).reduce((acc, [model, data]) => {
        acc[model] = Object.entries(data.fields).reduce((acc, [field, value]) => {
            acc[field] = value;
            return acc;
        }, {});
        return acc;
    }, {});
    const fields = Object.entries(this.models).reduce((acc, [model, data]) => {
        acc[model] = Object.keys(data.fields);
        return acc;
    }, {});
    for (const [model, data] of Object.entries(this.models)) {
        mockData[model] = {
            data: data.data,
            fields: fields[model],
            relations: relations[model],
        };
    }
    return mockData;
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
