import { expect, test } from "@odoo/hoot";
import {
    defineModels,
    getService,
    makeMockEnv,
    mockService,
    models,
} from "@web/../tests/web_test_helpers";

import { rpcBus } from "@web/core/network/rpc";

class Company extends models.Model {
    _name = "res.company";
}
class Notacompany extends models.Model {}

defineModels([Company, Notacompany]);

test("reload webclient when updating a res.company", async () => {
    mockService("action", {
        async doAction(action) {
            expect.step(action);
        },
    });
    await makeMockEnv();
    expect.verifySteps([]);
    await getService("orm").read("res.company", [32]);
    expect.verifySteps([]);
    await getService("orm").unlink("res.company", [32]);
    expect.verifySteps(["reload_context"]);
    await getService("orm").unlink("notacompany", [32]);
    expect.verifySteps([]);
});

test("do not reload webclient when updating a res.company, but there is an error", async () => {
    mockService("action", {
        async doAction(action) {
            expect.step(action);
        },
    });
    await makeMockEnv();
    expect.verifySteps([]);
    rpcBus.trigger("RPC:RESPONSE", {
        data: { params: { model: "res.company", method: "write" } },
        settings: {},
        result: {},
    });
    expect.verifySteps(["reload_context"]);
    rpcBus.trigger("RPC:RESPONSE", {
        data: { params: { model: "res.company", method: "write" } },
        settings: {},
        error: {},
    });
    expect.verifySteps([]);
});
