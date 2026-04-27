import { stockBarcodeProductExpiryModels } from "./stock_barcode_product_expiry_test_helpers.js";
import { expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import {
    defineActions,
    defineModels,
    getService,
    MockServer,
    mountWebClient,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

defineModels({
    ...stockBarcodeProductExpiryModels,
});

defineActions([
    {
        id: 1,
        name: "Stock Barcode",
        tag: "stock_barcode_client_action",
        type: "ir.actions.client",
        res_model: "stock.picking",
        context: { active_id: 1 },
    },
]);

onRpc("/stock_barcode/get_barcode_data", (...args) => ({
    data: {
        records: {
            "stock.picking": MockServer.current._models["stock.picking"],
            "stock.picking.type": MockServer.current._models["stock.picking.type"],
            "stock.move.line": MockServer.current._models["stock.move.line"],
            "product.product": MockServer.current._models["product.product"],
            "uom.uom": MockServer.current._models["uom.uom"],
            "stock.location": MockServer.current._models["stock.location"],
            "barcode.nomenclature": MockServer.current._models["barcode.nomenclature"],
        },
        nomenclature_id: 1,
    },
    groups: { group_uom: true },
}));

test("expiration date is rendered in user timezone", async () => {
    mockDate("2025-07-01 12:00:00", +2);
    await mountWebClient({ WebClient: WebClientEnterprise });
    await getService("action").doAction(1);
    expect(".o_barcode_line div[name=lot]").toHaveText("TEST LOT (06/16/2025)");
});
