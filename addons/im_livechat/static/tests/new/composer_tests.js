/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { dragenterFiles, start } from "@mail/../tests/helpers/test_utils";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";

let target;
QUnit.module("composer", {
    beforeEach() {
        target = getFixture();
    },
});

QUnit.test("No add attachments button", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "Livechat 1",
        channel_type: "livechat",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce(target, ".o-mail-composer");
    assert.containsNone(target, "button[title='Attach files']");
});

QUnit.test("Attachment upload via drag and drop disabled", async function (assert) {
    assert.expect(2);

    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "Livechat 1",
        channel_type: "livechat",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce(target, ".o-mail-composer");
    dragenterFiles(target.querySelector(".o-mail-composer-textarea"));
    await nextTick();
    assert.containsNone(target, ".o-dropzone");
});
