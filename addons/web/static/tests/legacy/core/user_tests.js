/** @odoo-module alias=@web/../tests/core/user_tests default=false */

import { _makeUser, user } from "@web/core/user";
import { makeTestEnv } from "../helpers/mock_env";
import { patchWithCleanup } from "../helpers/utils";

QUnit.module("User");

QUnit.test("successive calls to hasGroup", async (assert) => {
    patchWithCleanup(user, _makeUser({ uid: 7 }));
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
