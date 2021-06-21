/** @odoo-module **/

import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";
import { makeTestEnv } from "../helpers/mock_env";

const serviceRegistry = registry.category("services");

QUnit.module("UserService");

QUnit.test("successive calls to hasGroup", async (assert) => {
    serviceRegistry.add("user", userService);
    const groups = ["x"];
    const mockRPC = (route, args) => {
        assert.step(`${args.model}/${args.method}/${args.args[0]}`);
        return groups.includes(args.args[0]);
    };
    const env = await makeTestEnv({ mockRPC });
    let hasGroupX = await env.services.user.hasGroup("x");
    let hasGroupY = await env.services.user.hasGroup("y");
    assert.strictEqual(hasGroupX, true);
    assert.strictEqual(hasGroupY, false);
    let hasGroupXAgain = await env.services.user.hasGroup("x");
    assert.strictEqual(hasGroupXAgain, true);

    assert.verifySteps(["res.users/has_group/x", "res.users/has_group/y"]);
});
