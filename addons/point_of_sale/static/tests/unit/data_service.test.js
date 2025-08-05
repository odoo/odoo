<<<<<<< HEAD
||||||| MERGE BASE
=======
import { expect, test } from "@odoo/hoot";
import {
    defineModels,
    getService,
    makeMockEnv,
    models,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { RPCError } from "@web/core/network/rpc";

class PosSession extends models.ServerModel {
    _name = "pos.session";
    load_data_params() {
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
            },
            "product.product": { relations: {}, fields: {} },
            "product.template": { relations: {}, fields: {} },
            "product.pricelist": { relations: {}, fields: {} },
            "pos.session": { relations: {}, fields: {} },
            "res.company": {
                relations: {},
                fields: {
                    tax_calculation_rounding_method: {
                        string: "Tax rounding method",
                        type: "string",
                    },
                },
            },
            "stock.picking.type": { relations: {}, fields: {} },
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
            },
            "pos.printer": { relations: {}, fields: {} },
            "pos.payment.method": { relations: {}, fields: {} },
            "res.currency": {
                relations: {},
                fields: {
                    rounding: {
                        string: "Rounding",
                        type: "float",
                    },
                },
            },
            "res.users": { relations: {}, fields: {} },
            "account.fiscal.position": { relations: {}, fields: {} },
            "pos.category": { relations: {}, fields: {} },
            "pos.order": { relations: {}, fields: {} },
            "pos.order.line": { relations: {}, fields: {} },
            "pos.payment": { relations: {}, fields: {} },
            "pos.pack.operation.lot": { relations: {}, fields: {} },
            "product.pricelist.item": { relations: {}, fields: {} },
            "product.attribute.custom.value": { relations: {}, fields: {} },
        };
    }
    load_data() {
        return {
            "res.partner": [],
            "product.product": [],
            "product.template": [],
            "product.pricelist": [],
            "pos.session": [{ name: "PoS Session", id: 1 }],
            "res.company": [{ tax_calculation_rounding_method: "round_globally" }],
            "stock.picking.type": [],
            "pos.config": [
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
            "pos.printer": [],
            "pos.payment.method": [],
            "res.currency": [{ rounding: 0.01 }],
            "res.users": [{ id: 1, name: "Administrator" }],
            "account.fiscal.position": [],
            "pos.category": [],
            "pos.order": [],
            "pos.order.line": [],
            "pos.payment": [],
            "pos.pack.operation.lot": [],
            "product.pricelist.item": [],
            "product.attribute.custom.value": [],
        };
    }
}
class ResPartner extends models.ServerModel {
    _name = "res.partner";
    create() {
        const error = new RPCError();
        error.exceptionName = "odoo.exceptions.ValidationError";
        error.code = 0;
        error.message = "ValidationError";
        error.data = {
            name: "ValidationError",
        };
        throw error;
    }
}
test("don't retry sending data to the server if the reason that caused the failure is not a network error", async () => {
    onRpc("/pos/ping", () => {});
    defineModels({ PosSession, ResPartner });
    onRpc("pos.session", "filter_local_data", () => ({}));
    await makeMockEnv();

    await expect(
        getService("pos_data").create("res.partner", [{ name: "Test 1", vat: "BE40301926" }])
    ).rejects.toThrow();
    expect(getService("pos_data").network.unsyncData).toHaveLength(0);
});

>>>>>>> FORWARD PORTED
