import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "../../mail_test_helpers";
import { pttExtensionHookService } from "@mail/discuss/call/common/ptt_extension_service";
import { mockService } from "@web/../tests/web_test_helpers";
import { getMockEnv } from "@web/../tests/_framework/env_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("display banner when ptt extension is not enabled", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    mockService("discuss.ptt_extension", () => ({
        ...pttExtensionHookService.start(getMockEnv(), {}),
        get isEnabled() {
            return false;
        },
    }));
    patchUiSize({ size: SIZES.SM });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow");
    await click(".o-mail-ChatWindow-command", { text: "General" });
    await click(".o-mail-ChatWindow-command", { text: "Show Settings" });
    await click("button", { text: "Push to Talk" });
    await click("[title='Close panel']");
    await click("[title='Start a Call']");
    await contains(".o-discuss-PttAdBanner");
    await click("[title='Show Settings']");
    await click("button", { text: "Voice Detection" });
    await click("[title='Close panel']");
    await contains(".o-discuss-PttAdBanner", { count: 0 });
});
