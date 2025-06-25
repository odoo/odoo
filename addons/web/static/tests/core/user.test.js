import { test, expect, describe } from "@odoo/hoot";
import { _makeUser, user } from "@web/core/user";
import { makeMockEnv, onRpc, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

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
        expect.step(JSON.stringify(args.kwargs.new_settings));
        return { a: 3, c: 4 };
    });

    expect(user.settings).toEqual({ a: 1, b: 2 });

    await user.setUserSettings("a", 3);
    expect.verifySteps(['{"a":3}']);
    expect(user.settings).toEqual({ a: 3, b: 2, c: 4 });
});
