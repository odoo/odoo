/** @odoo-module */

import { test } from "@odoo/hoot";
import {
    click,
    contains,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
} from "../../mail_test_helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

test.skip("display banner when ptt extension is not enabled", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { env } = await start();
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
