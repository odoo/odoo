/** @odoo-module alias=@mail/../tests/discuss/call/ptt_ad_banner_tests default=false */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { mockGetMedia, start } from "@mail/../tests/helpers/test_utils";
import { click, contains } from "@web/../tests/utils";
import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("ptt ad banner");

QUnit.test("display banner when ptt extension is not enabled", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { env, openDiscuss } = await start();
    patchWithCleanup(env.services["discuss.ptt_extension"], {
        get isEnabled() {
            return false;
        },
    });
    await openDiscuss(channelId);
    await click("[title='Show Call Settings']");
    await click("[title='toggle push-to-talk']");
    await click("[title='Start a Call']");
    await contains(".o-discuss-PttAdBanner");
    await click("[title='toggle push-to-talk']");
    await contains(".o-discuss-PttAdBanner", { count: 0 });
});
