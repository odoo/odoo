import {
    click,
    defineMailModels,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { ActivityMenu } from "@mail/core/web/activity_menu";
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryText, waitFor, waitForNone } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("should update activities when opening the activity menu", async () => {
    const pyEnv = await startServer();
    await start();
    await waitFor(".o_menu_systray i[aria-label='Activities']:count(1)");
    await waitForNone(".o-mail-ActivityMenu-counter");
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        res_id: partnerId,
        res_model: "res.partner",
    });
    await click(".o_menu_systray i[aria-label='Activities']");
    await waitFor(".o-mail-ActivityMenu-counter:text('1'):count(1)");
});

test("global shortcut", async () => {
    await mountWithCleanup(ActivityMenu);
    await triggerHotkey("control+k");
    await animationFrame();
    expect(queryText(`.o_command:contains("Activity") .o_command_hotkey`)).toEqual(
        "Activity\nALT + SHIFT + A",
        { message: "The command should be registered with the right hotkey" }
    );
    await triggerHotkey("alt+shift+a");
    await animationFrame();
    expect(".modal-dialog .modal-title").toHaveText("Schedule Activity");
});
