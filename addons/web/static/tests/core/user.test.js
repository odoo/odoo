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

test("active companies are sorted", async () => {
    serverState.companies = [
        { id: 1, name: "Company 1", sequence: 1, parent_id: false, child_ids: [] },
        { id: 2, name: "Company 2", sequence: 2, parent_id: false, child_ids: [] },
        { id: 3, name: "Company 3", sequence: 3, parent_id: false, child_ids: [] },
    ];

    expect(user.activeCompanies.map((c) => c.id)).toEqual([1]);
    user.activateCompanies([2, 3, 1]);
    expect(user.activeCompanies.map((c) => c.id)).toEqual([2, 1, 3]);
});

test("activate company branches after access error", async () => {
    cookie.set("cids", "1");
    serverState.companies = [
        {
            id: 1,
            name: "Company 1",
            sequence: 1,
            parent_id: false,
            child_ids: [2, 3],
        },
        {
            id: 2,
            name: "Company 1 Branch 1",
            sequence: 2,
            parent_id: 1,
            child_ids: [],
        },
        {
            id: 3,
            name: "Company 1 Branch 2",
            sequence: 3,
            parent_id: 1,
            child_ids: [],
        },
    ];

    const activeCompanyIds = user.activeCompanies.map((c) => c.id);
    activeCompanyIds.push(2);
    user.activateCompanies(activeCompanyIds);
    // Activating the first branch should activate all branches
    expect(cookie.get("cids")).toBe("1-2-3");
});
