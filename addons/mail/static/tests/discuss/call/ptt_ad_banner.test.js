import {
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
import { contains } from "@web/../tests/web_test_helpers";

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
    await contains("[title='Open Actions Menu']:count(1)").click();
    await contains(".o-dropdown-item:text('Voice & Video Settings'):count(1)").click();
    await contains("label[aria-label='Enable Push-to-talk']:count(1)").click();
    await contains("[title*='Close Chat Window']:count(1)").click();
    await contains(".o-mail-MessagingMenu-tab[data-id='meeting']:count(1)").click();
    await contains("button:text('Meeting'):count(1)").click();
    await contains(".o-dropdown-item:text('Start Now'):count(1)").click();
    await waitFor(".o-mail-Meeting:count(1)");
    await waitFor(".o-discuss-PttAdBanner:count(1)");
    await contains("[title='Voice Settings']:count(1)").click();
    await contains(".dropdown-menu button:contains('Push-to-Talk'):count(1)").click();
    await waitForNone(".o-discuss-PttAdBanner");
});
