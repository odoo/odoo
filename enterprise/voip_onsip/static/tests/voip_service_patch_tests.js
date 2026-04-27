import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

QUnit.module("voip_service");

QUnit.test("authorizationUsername is overridden to use onsip_auth_username.", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        voip_username: "VoIP username",
        onsip_auth_username: "OnSIP username",
        user_id: serverState.userId,
    });
    const { env } = await start();
    assert.equal(env.services.voip.authorizationUsername, "OnSIP username");
});
