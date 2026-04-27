import { describe, test } from "@odoo/hoot";
import { click, contains, start } from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Clicking on systray item when softphone is hidden shows the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await contains(".o-voip-Softphone");
});

test("Clicking on systray item when softphone is displayed and unfolded hides the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o_menu_systray button[title='Close Softphone']");
    await contains(".o-voip-Softphone");
});

test("Clicking on systray item when softphone is displayed but folded unfolds the softphone.", async () => {
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".o-voip-Softphone-topbar"); // fold
    await click(".o_menu_systray button[title='Unfold Softphone']");
    await contains(".o-voip-Softphone-content");
});
