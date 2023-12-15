/** @odoo-module **/

import { _makeUser, user } from "@web/core/user";
import { makeTestEnv } from "../helpers/mock_env";
import { patchUserWithCleanup } from "../helpers/mock_services";

QUnit.module("User");

QUnit.test("successive calls to hasGroup", async (assert) => {
    patchUserWithCleanup(_makeUser());
    const groups = ["x"];
    const mockRPC = (route, args) => {
        assert.step(`${args.model}/${args.method}/${args.args[0]}`);
        return groups.includes(args.args[0]);
    };
    await makeTestEnv({ mockRPC });
    const hasGroupX = await user.hasGroup("x");
    const hasGroupY = await user.hasGroup("y");
    assert.strictEqual(hasGroupX, true);
    assert.strictEqual(hasGroupY, false);
    const hasGroupXAgain = await user.hasGroup("x");
    assert.strictEqual(hasGroupXAgain, true);

    assert.verifySteps(["res.users/has_group/x", "res.users/has_group/y"]);
});
