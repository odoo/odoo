import {
    click,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { pttExtensionServiceInternal } from "@mail/discuss/call/common/ptt_extension_service";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

test("display banner when ptt extension is not enabled", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    patch(pttExtensionServiceInternal, {
        onAnswerIsEnabled(pttService) {
            pttService.isEnabled = false;
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await waitFor("[title='Open Actions Menu']:count(1)");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item:text('Voice & Video Settings')");
    await click("label[aria-label='Enable Push-to-talk']");
    await click("[title*='Close Chat Window']");
    await click(".o-mail-MessagingMenu-tab[data-id='meeting']");
    await click("button:text('Meeting')");
    await click(".o-dropdown-item:text('Start Now')");
    await waitFor(".o-mail-Meeting:count(1)");
    await waitFor(".o-discuss-PttAdBanner:count(1)");
    await click("[title='Voice Settings']");
    await click(".dropdown-menu button:contains('Push-to-Talk')");
    await waitForNone(".o-discuss-PttAdBanner");
});
