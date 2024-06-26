import { expect, test } from "@odoo/hoot";
import {
    defineModels,
    getService,
    makeMockEnv,
    mockService,
    models,
    serverState,
} from "@web/../tests/web_test_helpers";

import { cookie } from "@web/core/browser/cookie";
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

test("extract allowed company ids from cookies", async () => {
    serverState.companies = [
        { id: 1, name: "Company 1", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Company 2", sequence: 2, parent_id: false, child_ids: [] },
        { id: 3, name: "Company 3", sequence: 3, parent_id: false, child_ids: [] },
    ];
    cookie.set("cids", "3-1");
    await makeMockEnv();
    expect(Object.values(getService("company").allowedCompanies).map((c) => c.id)).toEqual([
        1, 2, 3,
    ]);
    expect(getService("company").activeCompanyIds).toEqual([3, 1]);
    expect(getService("company").currentCompany.id).toBe(3);
});
