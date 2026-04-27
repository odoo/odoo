import { describe, expect, test } from "@odoo/hoot";
import { start, startServer } from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";
import { getService, patchWithCleanup, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

// allow test data to be overridden in other modules
const settingsData = {
    voip_secret: "super secret password",
    voip_username: "1337",
};
const expectedValues = {
    authorizationUsername: settingsData.voip_username,
};

test("SIP.js user agent configuration is set correctly.", async (assert) => {
    patchWithCleanup(window, {
        SIP: {
            UserAgent: {
                makeURI(uri) {
                    const [, scheme, user, host, port] = uri.match(
                        /([^:]+):([^@]+)@([^:]+):?(\d+)?/
                    );
                    const raw = { host, port, scheme, user };
                    return { raw };
                },
            },
            Web: {
                defaultSessionDescriptionHandlerFactory() {},
            },
        },
    });
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        ...settingsData,
        user_id: serverState.userId,
    });
    await start();
    const config = (await getService("voip.user_agent")).sipJsUserAgentConfig;
    expect(config.authorizationPassword).toBe("super secret password");
    expect(config.authorizationUsername).toBe(expectedValues.authorizationUsername);
    expect(config.uri.raw.user).toBe("1337");
    expect(config.uri.raw.host).toBe("localhost");
});
