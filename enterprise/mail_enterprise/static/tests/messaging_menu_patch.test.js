import {
    click,
    contains,
    defineMailModels,
    patchUiSize,
    SIZES,
    start,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { methods } from "@web_mobile/js/services/core";

describe.current.tags("desktop");
defineMailModels();

test("'backbutton' event should close messaging menu", async () => {
    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {},
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");

    await contains(".o-mail-MessagingMenu");
    // simulate 'backbutton' event triggered by the mobile app
    const backButtonEvent = new Event("backbutton");
    document.dispatchEvent(backButtonEvent);
    await contains(".o-mail-MessagingMenu", { count: 0 });
});

test("[technical] messaging menu should properly override the back button", async () => {
    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    let overrideBackButton = false;
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {
            overrideBackButton = enabled;
        },
    });
    patchUiSize({ size: SIZES.SM });
    await start();

    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu");
    expect(overrideBackButton).toBe(true);

    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-MessagingMenu", { count: 0 });
    expect(overrideBackButton).toBe(false);
});
