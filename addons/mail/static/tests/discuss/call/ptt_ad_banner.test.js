import { pttExtensionHookService } from "@mail/discuss/call/common/ptt_extension_service";
import { describe, test } from "@odoo/hoot";
import { mockService } from "@web/../tests/web_test_helpers";
import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
} from "../../mail_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("display banner when ptt extension is not enabled", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    mockService("discuss.ptt_extension", (...args) => {
        const service = pttExtensionHookService.start(...args);
        Object.defineProperty(service, "isEnabled", {
            get() {
                return false;
            },
        });
        return service;
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Show Call Settings']");
    await click("[title='toggle push-to-talk']");
    await click("[title='Start a Call']");
    await contains(".o-discuss-PttAdBanner");
    await click("[title='toggle push-to-talk']");
    await contains(".o-discuss-PttAdBanner", { count: 0 });
});
