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
}
class Notcurrency extends models.Model {}

defineModels([Currency, Notcurrency]);

test("reload currencies when updating a res.currency", async () => {
    onRpc(({ route }) => {
        expect.step(route);
    });
    onRpc("/web/session/get_session_info", ({ url }) => {
        expect.step(new URL(url).pathname);
        return {
            uid: 1,
            currencies: {
                7: { symbol: "$", position: "before", digits: 2 },
            },
        };
    });
    await makeMockEnv();
    expect.verifySteps([]);
    await getService("orm").read("res.currency", [32]);
    expect.verifySteps(["/web/dataset/call_kw/res.currency/read"]);
    await getService("orm").unlink("res.currency", [32]);
    expect.verifySteps([
        "/web/dataset/call_kw/res.currency/unlink",
        "/web/session/get_session_info",
    ]);
    await getService("orm").unlink("notcurrency", [32]);
    expect.verifySteps(["/web/dataset/call_kw/notcurrency/unlink"]);
    expect(Object.keys(currencies)).toEqual(["7"]);
});

test("do not reload webclient when updating a res.currency, but there is an error", async () => {
    onRpc("/web/session/get_session_info", ({ url }) => {
        expect.step(new URL(url).pathname);
    });
    await makeMockEnv();
    expect.verifySteps([]);
    rpcBus.trigger("RPC:RESPONSE", {
        data: { params: { model: "res.currency", method: "write" } },
        settings: {},
        result: {},
    });
    expect.verifySteps(["/web/session/get_session_info"]);
    rpcBus.trigger("RPC:RESPONSE", {
        data: { params: { model: "res.currency", method: "write" } },
        settings: {},
        error: {},
    });
    expect.verifySteps([]);
});
