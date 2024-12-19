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

test("company evalContext", async () => {
    serverState.companies = [
        {
            id: 1,
            name: "Company 1",
            sequence: 1,
            parent_id: false,
            child_ids: [],
            country_code: "BE",
        },
        {
            id: 2,
            name: "Company 2",
            sequence: 2,
            parent_id: false,
            child_ids: [],
            country_code: "PE",
        },
        {
            id: 3,
            name: "Company 3",
            sequence: 3,
            parent_id: false,
            child_ids: [],
            country_code: "AR",
        },
    ];
    cookie.set("cids", "3-1");
    await makeMockEnv();

    const companyEvalContext = getService("company").evalContext;

    expect(companyEvalContext.allowed_ids).toEqual([1, 2, 3]);
    expect(companyEvalContext.active_ids).toEqual([3, 1]);
    expect(companyEvalContext.active_id).toBe(3);
    expect(companyEvalContext.multi_company).toBe(true);

    // check if the active_id has as contry_code AR
    expect(companyEvalContext.has(companyEvalContext.active_id, "country_code", "AR")).toBe(true);
    // check if the active_id has as contry_code PE
    expect(companyEvalContext.has(companyEvalContext.active_id, "country_code", "PE")).toBe(false);

    // check if one of the active_ids has as contry_code AR
    expect(companyEvalContext.has(companyEvalContext.active_ids, "country_code", "AR")).toBe(true);
    // check if one of the active_ids has as contry_code BE
    expect(companyEvalContext.has(companyEvalContext.active_ids, "country_code", "BE")).toBe(true);
    // check if one of the active_ids has as contry_code PE
    expect(companyEvalContext.has(companyEvalContext.active_ids, "country_code", "PE")).toBe(false);

    // check if one of the allowed_ids has as contry_code AR
    expect(companyEvalContext.has(companyEvalContext.allowed_ids, "country_code", "PE")).toBe(true);
    // check if one of the allowed_ids has as contry_code BR
    expect(companyEvalContext.has(companyEvalContext.allowed_ids, "country_code", "BR")).toBe(
        false
    );

    // If the company don't exist in the list, return always false
    expect(companyEvalContext.has(false, "country_code", "AR")).toBe(false);
    expect(companyEvalContext.has(4, "country_code", "AR")).toBe(false);
});
