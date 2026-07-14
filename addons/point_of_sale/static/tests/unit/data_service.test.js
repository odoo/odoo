import { expect, test } from "@odoo/hoot";
import { defineModels, makeMockEnv, models } from "@web/../tests/web_test_helpers";
import { RPCError } from "@web/core/network/rpc";

class PosSession extends models.ServerModel {
    _name = "pos.session";
    load_data() {
        return {
            "res.partner": {
                relations: {
                    vat: {
                        compute: false,
                        name: "vat",
                        related: false,
                        type: "char",
                    },
                    name: {
                        compute: false,
                        name: "name",
                        related: false,
                        type: "char",
                    },
                },
                fields: ["vat", "name"],
                data: [],
            },
            "product.product": { relations: {}, fields: {}, data: [] },
            "product.pricelist": { relations: {}, fields: {}, data: [] },
            "pos.session": {
                relations: {},
                fields: {},
                data: [
                    {
                        name: "PoS Session",
                        id: 1,
                    },
                ],
            },
            "res.company": {
                relations: {},
                fields: {
                    tax_calculation_rounding_method: {
                        string: "Tax rounding method",
                        type: "string",
                    },
                },
                data: [
                    {
                        tax_calculation_rounding_method: "round_globally",
                    },
                ],
            },
            "stock.picking.type": { relations: {}, fields: {}, data: [] },
            "pos.config": {
                relations: {},
                fields: {
                    iface_printer: {
                        string: "Iface printer",
                        type: "boolean",
                    },
                    trusted_config_ids: {
                        string: "Trusted config ids",
                        type: "many2many",
                    },
                },
                data: [
                    {
                        id: 1,
                        name: "PoS Config",
                        iface_printer: false,
                        trusted_config_ids: [2],
                    },
                    {
                        id: 2,
                        name: "PoS Config 2",
                        iface_printer: true,
                        trusted_config_ids: [1],
                    },
                ],
            },
            "pos.printer": { relations: {}, fields: {}, data: [] },
            "pos.payment.method": { relations: {}, fields: {}, data: [] },
            "res.currency": {
                relations: {},
                fields: {
                    rounding: {
                        string: "Rounding",
                        type: "float",
                    },
                },
                data: [
                    {
                        rounding: 0.01,
                    },
                ],
            },
            "res.users": {
                relations: {},
                fields: {},
                data: [
                    {
                        id: 1,
                        name: "Administrator",
                    },
                ],
            },
            "account.fiscal.position": { relations: {}, fields: {}, data: [] },
            "pos.category": { relations: {}, fields: {}, data: [] },
            "pos.order": { relations: {}, fields: {}, data: [] },
            "pos.order.line": { relations: {}, fields: {}, data: [] },
            "pos.payment": { relations: {}, fields: {}, data: [] },
            "pos.pack.operation.lot": { relations: {}, fields: {}, data: [] },
            "product.pricelist.item": { relations: {}, fields: {}, data: [] },
            "product.attribute.custom.value": { relations: {}, fields: {}, data: [] },
        };
    }
}
class ResPartner extends models.ServerModel {
    _name = "res.partner";
    create() {
        const error = new RPCError();
        error.exceptionName = "odoo.exceptions.ValidationError";
        error.code = 200;
        error.message = "ValidationError";
        error.data = {
            name: "ValidationError",
        };
        throw error;
    }
}
test("don't retry sending data to the server if the reason that caused the failure is not a network error", async () => {
    await defineModels({ PosSession, ResPartner });
    const env = await makeMockEnv();
    try {
        await env.services.pos_data.create("res.partner", [{ name: "Test 1", vat: "BE40301926" }]);
    } catch {
        expect.step("create failed");
        expect(env.services.pos_data.network.unsyncData.length).toBe(0);
    }
    expect.verifySteps(["create failed"]);
});
