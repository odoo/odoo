import { expect, test } from "@odoo/hoot";
import {
    defineModels,
    getService,
    makeMockEnv,
    models,
    onRpc,
} from "@web/../tests/web_test_helpers";

import { currencies } from "@web/core/currency";
import { rpcBus } from "@web/core/network/rpc";

class Currency extends models.Model {
    _name = "res.currency";
    get_all_currencies() {
        return {
            1: { symbol: "$", position: "before", digits: 2 },
        };
    }
}
class Notcurrency extends models.Model {}

defineModels([Currency, Notcurrency]);

test("reload currencies when updating a res.currency", async () => {
    onRpc(({ route }) => {
        expect.step(route);
    });
    await makeMockEnv();
    expect.verifySteps([]);
    await getService("orm").read("res.currency", [32]);
    expect.verifySteps(["/web/dataset/call_kw/res.currency/read"]);
    await getService("orm").unlink("res.currency", [32]);
    expect.verifySteps([
        "/web/dataset/call_kw/res.currency/unlink",
        "/web/dataset/call_kw/res.currency/get_all_currencies",
    ]);
    await getService("orm").unlink("notcurrency", [32]);
    expect.verifySteps(["/web/dataset/call_kw/notcurrency/unlink"]);
    expect(Object.keys(currencies)).toEqual(["1"]);
});

test("do not reload webclient when updating a res.currency, but there is an error", async () => {
    onRpc("/web/dataset/call_kw/res.currency/get_all_currencies", ({ url }) => {
        expect.step(new URL(url).pathname);
    });
    await makeMockEnv();
    expect.verifySteps([]);
    rpcBus.trigger("RPC:RESPONSE", {
        data: { params: { model: "res.currency", method: "write" } },
        settings: {},
        result: {},
    });
    expect.verifySteps(["/web/dataset/call_kw/res.currency/get_all_currencies"]);
    rpcBus.trigger("RPC:RESPONSE", {
        data: { params: { model: "res.currency", method: "write" } },
        settings: {},
        error: {},
    });
    expect.verifySteps([]);
});
