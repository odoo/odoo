/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { triggerHotkey, patchWithCleanup } from "@web/../tests/helpers/utils";
import { contains, insertText, click } from "@web/../tests/utils";
import { browser } from "@web/core/browser/browser";

QUnit.module("mobile composer");

QUnit.test(
    'Mobile: enter key should create a newline in composer',
    async () => {
        const pyEnv = await startServer();
        pyEnv["discuss.channel"].create({ name: "General" });
        // patching navigator to fake a mobile device
        patchWithCleanup(browser.navigator, {
            userAgent: "Chrome/0.0.0 Android (OdooMobile; Linux; Android 13; Odoo TestSuite)",
        });
        const { openDiscuss } = await start();
        openDiscuss();
        await click(".o-mail-MessagingMenu-tab", { text: "Channel" });
        await click(".o-mail-NotificationItem", { text: "General" });
        await insertText(".o-mail-Composer-input", "Test\n");
        triggerHotkey("Enter");
        await insertText(".o-mail-Composer-input", "Other");
        await click(".o-mail-Composer-send");
        await contains(".o-mail-Message-body");
        await contains(".o-mail-Message-body:has(br)", { textContent: "TestOther" });
    }
)
