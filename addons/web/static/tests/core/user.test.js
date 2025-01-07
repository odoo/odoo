import { test, expect, describe } from "@odoo/hoot";
import { _makeUser, user } from "@web/core/user";
import { makeMockEnv, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";
import { cookie } from "@web/core/browser/cookie";

describe.current.tags("headless");

test("successive calls to hasGroup", async () => {
    serverState.uid = 7;
    await makeMockEnv();
    const groups = ["x"];
    onRpc("has_group", (args) => {
        expect.step(`${args.model}/${args.method}/${args.args[1]}`);
        return groups.includes(args.args[1]);
    });

    const hasGroupX = await user.hasGroup("x");
    const hasGroupY = await user.hasGroup("y");
    expect(hasGroupX).toBe(true);
    expect(hasGroupY).toBe(false);
    const hasGroupXAgain = await user.hasGroup("x");
    expect(hasGroupXAgain).toBe(true);

    expect.verifySteps(["res.users/has_group/x", "res.users/has_group/y"]);
});

test("set user settings do not override old valid keys", async () => {
    await makeMockEnv();
    patchWithCleanup(user, _makeUser({ user_settings: { a: 1, b: 2 } }));
    onRpc("set_res_users_settings", (args) => {
        expect.step(args.kwargs.new_settings);
        return { a: 3, c: 4 };
    });

    expect(user.settings).toEqual({ a: 1, b: 2 });

    await user.setUserSettings("a", 3);
    expect.verifySteps([{ a: 3 }]);
    expect(user.settings).toEqual({ a: 3, b: 2, c: 4 });
});

test("extract allowed company ids from cookies", async () => {
    // cookies need to be set before the serverState
    // the modification of the serverState will force the re-creation of the user with the new values (see mock_user.hoot.js)
    cookie.set("cids", "3-1");
    serverState.companies = [
        { id: 1, name: "Company 1", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Company 2", sequence: 2, parent_id: false, child_ids: [] },
        { id: 3, name: "Company 3", sequence: 3, parent_id: false, child_ids: [] },
    ];

    expect(user.allowedCompanies.map((c) => c.id)).toEqual([1, 2, 3]);
    expect(user.activeCompanies.map((c) => c.id)).toEqual([3, 1]);
    expect(user.activeCompany.id).toBe(3);
});

test("company evalContext", async () => {
    cookie.set("cids", "3-1");
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

    // Test that the patch works correctly.
    expect(user.activeCompanies.map((c) => c.id)).toEqual([3, 1]);
    expect(user.activeCompany.id).toBe(3);

    const companyEvalContext = user.evalContext.companies;

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
