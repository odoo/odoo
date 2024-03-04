/** @odoo-module **/

import { registry } from "@web/core/registry";
import { userService } from "@web/core/user_service";
import { makeTestEnv } from "../helpers/mock_env";
import { session } from "@web/session";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

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
    const hasGroupX = await env.services.user.hasGroup("x");
    const hasGroupY = await env.services.user.hasGroup("y");
    assert.strictEqual(hasGroupX, true);
    assert.strictEqual(hasGroupY, false);
    const hasGroupXAgain = await env.services.user.hasGroup("x");
    assert.strictEqual(hasGroupXAgain, true);

    assert.verifySteps(["res.users/has_group/x", "res.users/has_group/y"]);
});

QUnit.test("set user settings do not override old valid keys", async (assert) => {
    patchWithCleanup(session, {
        ...session,
        user_settings: { a: 1, b: 2 },
    });
    serviceRegistry.add("user", userService);

    const mockRPC = (route, args) => {
        assert.step(JSON.stringify(args.kwargs.new_settings));
        return { a: 3, c: 4 };
    };
    const env = await makeTestEnv({ mockRPC });
    assert.deepEqual(env.services.user.settings, { a: 1, b: 2 });

    await env.services.user.setUserSettings("a", 3);
    assert.verifySteps(['{"a":3}']);
    assert.deepEqual(env.services.user.settings, { a: 3, b: 2, c: 4 });
});
