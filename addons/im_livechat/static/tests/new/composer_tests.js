/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { click, dragenterFiles, start } from "@mail/../tests/helpers/test_utils";
import { editInput, getFixture, nextTick, triggerHotkey } from "@web/../tests/helpers/utils";

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

QUnit.test("Can execute help command on livechat channels", async function (assert) {
    const pyEnv = await startServer();
    pyEnv["mail.channel"].create({
        anonymous_name: "Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    await start({
        mockRPC(route, args, originalMockRPC) {
            if (args.method === "execute_command_help") {
                assert.step("execute_command_help");
                return true;
            }
            return originalMockRPC(route, args);
        },
    });
    await click(".o_menu_systray i[aria-label='Messages']");
    await click(".o-mail-notification-item");
    await editInput(target, ".o-mail-composer-textarea", "/help");
    triggerHotkey("Enter");
    await nextTick();
    assert.verifySteps(["execute_command_help"]);
});
