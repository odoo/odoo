import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("display banner when ptt extension is not enabled", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockService("discuss.ptt_extension", {
        get isEnabled() {
            return false;
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await click("button", { text: "Push to Talk" });
    await click("[title*='Close Chat Window']");
    await click("button", { text: "Start a meeting" });
    await click("button[title='Close panel']"); // invitation panel automatically open
    await contains(".o-discuss-PttAdBanner");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await click("button", { text: "Voice Detection" });
    await click("[title*='Close Chat Window']");
    await contains(".o-discuss-PttAdBanner", { count: 0 });
});
