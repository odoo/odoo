/** @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { afterNextRender, click, dragenterFiles, start } from "@mail/../tests/helpers/test_utils";
import { editInput, nextTick, triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("composer");

QUnit.test("No add attachments button", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "Livechat 1",
        channel_type: "livechat",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Composer");
    assert.containsNone($, "button[title='Attach files']");
});

QUnit.test("Attachment upload via drag and drop disabled", async (assert) => {
    assert.expect(2);

    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        name: "Livechat 1",
        channel_type: "livechat",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Composer");
    dragenterFiles($(".o-Composer-input")[0]);
    await nextTick();
    assert.containsNone($, ".o-Dropzone");
});

QUnit.test("Can execute help command on livechat channels", async (assert) => {
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
    await click(".o-NotificationItem");
    await editInput(document.body, ".o-Composer-input", "/help");
    triggerHotkey("Enter");
    await nextTick();
    assert.verifySteps(["execute_command_help"]);
});

QUnit.test('Receives visitor typing status "is typing"', async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        anonymous_name: "Visitor 20",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { env, openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.strictEqual($(".o-Typing").text(), "");
    const channel = pyEnv["mail.channel"].searchRead([["id", "=", channelId]])[0];
    // simulate receive typing notification from livechat visitor "is typing"
    await afterNextRender(() =>
        env.services.rpc("/im_livechat/notify_typing", {
            context: { mockedPartnerId: pyEnv.publicPartnerId },
            is_typing: true,
            uuid: channel.uuid,
        })
    );
    assert.containsOnce($, ".o-Typing:contains(Visitor 20 is typing...)");
});
