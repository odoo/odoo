/** @odoo-module **/

import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { currencies } from "@web/core/currency";
import { currencyService } from "@web/webclient/currency_service";
import { makeTestEnv } from "../helpers/mock_env";
import { makeFakeRPCService } from "../helpers/mock_services";

const serviceRegistry = registry.category("services");

QUnit.module("currency service");

QUnit.test("reload currencies when updating a res.currency", async (assert) => {
    serviceRegistry.add("currency", currencyService);
    serviceRegistry.add("orm", ormService);
    const fakeRpc = makeFakeRPCService((route) => {
        assert.step(route);
        if (route === "/web/session/get_session_info") {
            return {
                uid: 1,
                currencies: {
                    7: { symbol: "$", position: "before", digits: 2 },
                },
            };
        }
    });
    serviceRegistry.add("rpc", fakeRpc);
    const env = await makeTestEnv();
    assert.verifySteps([]);
    await env.services.orm.read("res.currency", [32]);
    assert.verifySteps(["/web/dataset/call_kw/res.currency/read"]);
    await env.services.orm.unlink("res.currency", [32]);
    assert.verifySteps([
        "/web/dataset/call_kw/res.currency/unlink",
        "/web/session/get_session_info",
    ]);
    await env.services.orm.unlink("notcurrency", [32]);
    assert.verifySteps(["/web/dataset/call_kw/notcurrency/unlink"]);
    assert.deepEqual(Object.keys(currencies), ["7"]);
});

QUnit.test(
    "do not reload webclient when updating a res.currency, but there is an error",
    async (assert) => {
        const fakeRpc = makeFakeRPCService((route) => {
            assert.step(route);
        });
        serviceRegistry.add("rpc", fakeRpc);
        serviceRegistry.add("currency", currencyService);

        const env = await makeTestEnv();
        assert.verifySteps([]);
        env.bus.trigger("RPC:RESPONSE", {
            data: { params: { model: "res.currency", method: "write" } },
            settings: {},
            result: {},
        });
        assert.verifySteps(["/web/session/get_session_info"]);
        env.bus.trigger("RPC:RESPONSE", {
            data: { params: { model: "res.currency", method: "write" } },
            settings: {},
            error: {},
        });
        assert.verifySteps([]);
    }
);
