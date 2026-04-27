import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { click, contains, patchUiSize, start } from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";

describe.current.tags("mobile");
setupVoipTests();

test("Clicking on the top bar does not fold the softphone window on small devices.", async () => {
    patchUiSize({ width: 360, height: 800 });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-Softphone-topbar");
    await tick();
    await contains(".o-voip-Softphone-content");
});

test("The cursor when hovering over the top bar is not a pointer on small devices.", async (assert) => {
    patchUiSize({ width: 360, height: 800 });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone");
    expect(".o-voip-Softphone-topbar:first").toHaveStyle({ cursor: "auto" });
});
