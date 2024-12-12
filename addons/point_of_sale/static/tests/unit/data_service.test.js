import { expect, test } from "@odoo/hoot";
import { defineModels, getService, makeMockEnv, models } from "@web/../tests/web_test_helpers";
import { RPCError } from "@web/core/network/rpc";
import { delay } from "@web/core/utils/concurrency";

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
            "pos.order": {
                relations: {
                    pos_reference: {
                        compute: false,
                        name: "pos_reference",
                        related: false,
                        type: "char",
                    },
                    lines: {
                        compute: false,
                        name: "lines",
                        related: true,
                        type: "one2many",
                        relation: "pos.order.line",
                    },
                    uuid: {
                        compute: false,
                        name: "uuid",
                        related: false,
                        type: "char",
                    },
                },
                fields: {
                    pos_reference: {
                        string: "PoS Reference",
                        type: "char",
                    },
                    lines: {
                        string: "Lines",
                        type: "one2many",
                        relation: "pos.order.line",
                    },
                },
            },
            "pos.order.line": {
                relations: {
                    qty: {
                        compute: false,
                        name: "qty",
                        related: false,
                        type: "float",
                    },
                    product_id: {
                        compute: false,
                        name: "product_id",
                        related: false,
                        type: "many2one",
                        relation: "product.product",
                    },
                    uuid: {
                        compute: false,
                        name: "uuid",
                        related: false,
                        type: "char",
                    },
                },
                fields: {
                    product_id: {
                        string: "Product",
                        type: "many2one",
                        relation: "product.product",
                    },
                    qty: {
                        string: "Quantity",
                        type: "float",
                    },
                },
            },
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

function isLikeUUID(str) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    return uuidRegex.test(str);
}
const state = {};
class PosConfig extends models.ServerModel {
    _name = "pos.config";
    flush(self, queue, login_number) {
        const expectedQueue = [
            [
                "CREATE",
                "pos.order.line",
                { qty: 1, product_id: 1, uuid: state.order.lines[0].uuid },
            ],
            [
                "CREATE",
                "pos.order.line",
                { qty: 2, product_id: 2, uuid: state.order.lines[1].uuid },
            ],
            [
                "CREATE",
                "pos.order",
                {
                    pos_reference: "1stOrder",
                    lines: state.order.lines.map((line) => line.uuid),
                    uuid: state.order.uuid,
                },
            ],
        ];
        for (const [method, , vals] of queue) {
            if (method === "CREATE") {
                expect(isLikeUUID(vals.uuid)).toBe(true);
            }
        }
        expect(JSON.stringify(queue)).toBe(JSON.stringify(expectedQueue));
        return {
            [state.order.lines[0].uuid]: 1,
            [state.order.lines[1].uuid]: 2,
            [state.order.uuid]: 1,
        };
    }
}

test("check that flushing works", async () => {
    defineModels({ PosSession, ResPartner, PosConfig });
    await makeMockEnv();

    const data_service = getService("pos_data");
    const order = data_service.models["pos.order"].create({
        pos_reference: "1stOrder",
        field_that_should_be_ignored: "let's see",
        lines: [
            ["create", { product_id: 1, qty: 1 }],
            ["create", { product_id: 2, qty: 2 }],
        ],
    });
    state.order = order;
    expect(data_service.idUpdates).toEqual({});
    await delay(1100);
    expect(data_service.idUpdates).toEqual({
        [order.lines[0].uuid]: 1,
        [order.lines[1].uuid]: 2,
        [order.uuid]: 1,
    });
});

/**
 * // TODO
 * test update, delete
 * test models with date fields
 */
