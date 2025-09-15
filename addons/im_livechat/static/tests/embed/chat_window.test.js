import { waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    click,
    contains,
    inputFiles,
    insertText,
    onRpcBefore,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { getService, serverState } from "@web/../tests/web_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { getOrigin } from "@web/core/utils/urls";

describe.current.tags("desktop");
defineLivechatModels();

test("internal users can upload file to temporary thread", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const [partnerUser] = pyEnv["res.users"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: partnerUser });
    await click(".o-livechat-LivechatButton");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await contains(".o-mail-Composer");
    await click(".o-mail-Composer button[title='More Actions']");
    await contains(".dropdown-item:contains('Attach files')");
    await inputFiles(".o-mail-Composer .o_input_file", [file]);
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt) .fa-check");
    await triggerHotkey("Enter");
    await contains(".o-mail-Message .o-mail-AttachmentContainer:contains(text.txt)");
});

test("The name of the conversation changes based on the agents' names", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header", { text: "MitchellOp" });
    await insertText(".o-mail-Composer-input", "Hello World!");
    await triggerHotkey("Enter");
    await waitUntilSubscribe();
    const [channelId] = pyEnv["discuss.channel"].search([
        ["channel_type", "=", "livechat"],
        [
            "channel_member_ids",
            "in",
            pyEnv["discuss.channel.member"].search([["guest_id", "=", pyEnv.cookie.get("dgid")]]),
        ],
    ]);
    const userId = pyEnv["res.users"].create({
        name: "James",
    });
    const secondAgent = pyEnv["res.partner"].create({
        lang: "en",
        name: "James",
        user_ids: [userId],
    });
    getService("orm").call("discuss.channel", "add_members", [[channelId]], {
        partner_ids: [secondAgent],
    });
    await contains(".o-mail-ChatWindow-header", { text: "MitchellOp, James" });
});

test("avatar url contains access token for non-internal users", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    const [partner] = pyEnv["res.partner"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(
        `.o-mail-ChatWindow-threadAvatar img[data-src="${getOrigin()}/web/image/res.partner/${
            partner.id
        }/avatar_128?access_token=${partner.id}&unique=${
            deserializeDateTime(partner.write_date).ts
        }"]`
    );
    await contains(
        `.o-mail-Message-avatar[data-src="${getOrigin()}/web/image/res.partner/${
            partner.id
        }/avatar_128?access_token=${partner.id}&unique=${
            deserializeDateTime(partner.write_date).ts
        }"]`
    );
    await insertText(".o-mail-Composer-input", "Hello World!");
    triggerHotkey("Enter");
    const guestId = pyEnv.cookie.get("dgid");
    const [guest] = pyEnv["mail.guest"].read(guestId);
    await contains(
        `.o-mail-Message-avatar[data-src="${getOrigin()}/web/image/mail.guest/${
            guest.id
        }/avatar_128?access_token=${guest.id}&unique=${deserializeDateTime(guest.write_date).ts}"]`
    );
});

test("can close confirm livechat with keyboard", async () => {
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore((route) => {
        if (route === "/im_livechat/visitor_leave_session") {
            expect.step(route);
        }
    });
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow");
    await insertText(".o-mail-Composer-input", "Hello");
    await triggerHotkey("Enter");
    await contains(".o-mail-Thread:not([data-transient])");
    await triggerHotkey("Escape");
    await contains(".o-livechat-CloseConfirmation", {
        text: "Leaving will end the live chat. Do you want to proceed?",
    });
    await triggerHotkey("Escape");
    await contains(".o-livechat-CloseConfirmation", { count: 0 });
    await triggerHotkey("Escape");
    await contains(".o-livechat-CloseConfirmation", {
        text: "Leaving will end the live chat. Do you want to proceed?",
    });
    await triggerHotkey("Enter");
    await expect.waitForSteps(["/im_livechat/visitor_leave_session"]);
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
});
