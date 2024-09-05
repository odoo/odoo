const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import { loadDefaultConfig, start } from "@im_livechat/../tests/embed/helper/test_utils";

import { patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";
import { createFile, inputFiles } from "@web/../tests/legacy/utils";
import { waitUntilSubscribe } from "@bus/../tests/legacy/helpers/websocket_event_deferred";

QUnit.module("chat window");

test("do not save fold state of temporary live chats", async () => {
    patchWithCleanup(LivechatButton, {
        DEBOUNCE_DELAY: 0,
    });
    await startServer();
    await loadDefaultConfig();
    await start({
        mockRPC(route, args) {
            if (route === "/discuss/channel/fold") {
                step(`fold - ${args.state}`);
            }
        },
    });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await insertText(".o-mail-Composer-input", "Hello");
    await triggerHotkey("Enter");
    await waitUntilSubscribe();
    await contains(".o-mail-Message", { text: "Hello" });
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-Message", { text: "Hello", count: 0 });
    await assertSteps(["fold - folded"]);
    await click("[title='Close Chat Window']");
    await click("button", { text: "Close conversation" });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await click(".o-mail-ChatWindow-header");
    await assertSteps([]);
});

QUnit.test("internal users can upload file to temporary thread", async () => {
    const pyEnv = await startServer();
    await loadDefaultConfig();
    await start();
    const [adminUser] = pyEnv["res.users"].search_read([["id", "=", pyEnv.adminUserId]]);
    pyEnv.authenticate(adminUser.login, adminUser.password);
    await click(".o-livechat-LivechatButton");
    const file = await createFile({
        content: "hello, world",
        contentType: "text/plain",
        name: "text.txt",
    });
    await contains(".o-mail-Composer");
    await contains("button[title='Attach files']");
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [file]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });
    await triggerHotkey("Enter");
    await contains(".o-mail-Message .o-mail-AttachmentCard", { text: "text.txt" });
});
