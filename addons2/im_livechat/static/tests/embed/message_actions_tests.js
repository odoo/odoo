/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("message actions");

QUnit.test("Only two quick actions are shown", async () => {
    // This is desired because 2 actions share a same icon
    // "Add a reaction" and "View reactions".
    await startServer();
    await loadDefaultConfig();
    start();
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    await click("[title='Add a Reaction']");
    await click(".o-Emoji", { text: "😅" });
    await contains(".o-mail-Message-actions i", { count: 3 });
    await contains("[title='Add a Reaction']");
    await contains("[title='Reply']");
    await contains("[title='Expand']");
    await click("[title='Expand']");
    await contains(".o-mail-Message-actions i", { count: 6 });
    await contains("[title='Edit']");
    await contains("[title='Delete']");
    await contains("[title='View Reactions']");
});
