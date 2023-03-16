/** @odoo-module **/

import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
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
});
