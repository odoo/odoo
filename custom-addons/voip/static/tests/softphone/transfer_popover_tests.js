/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("transfer_popover");

QUnit.test("TransferPopover input is pre-filled with external device number.", async () => {
    const externalDeviceNumber = "1337";
    const pyEnv = await startServer();
    pyEnv["res.users.settings"].create({
        external_device_number: externalDeviceNumber,
        user_id: pyEnv.currentUserId,
    });
    const { advanceTime, env } = await start({ hasTimeControl: true });
    // wait for external_device_number to be fetched
    await env.services["voip"].isReady;
    await click(".o_menu_systray button[title='Open Softphone']");
    await click("button[title='Open Numpad']");
    await insertText("input[placeholder='Enter the number…']", "+380 (44) 4315351");
    await triggerHotkey("Enter");
    await advanceTime(5000);
    await click("button[title='Transfer']:enabled");
    await contains(".o-voip-TransferPopover input", { value: externalDeviceNumber });
});
