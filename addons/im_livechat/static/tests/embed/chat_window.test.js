import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import {
    assertChatBubbleAndWindowImStatus,
    click,
    contains,
    inputFiles,
    insertText,
    mockGetMedia,
    onRpcBefore,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { asyncStep, serverState, waitForSteps, withUser } from "@web/../tests/web_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
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

test("Conversation name is operator livechat user name", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    await start({ authenticateAs: false });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header", { text: "MitchellOp" });
});

test("Portal users should not be able to start a call", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const joelUid = pyEnv["res.users"].create({
        name: "Joel",
        share: true,
        login: "joel",
        password: "joel",
    });
    const joelPid = pyEnv["res.partner"].create({
        name: "Joel",
        user_ids: [joelUid],
    });
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    await start({ authenticateAs: { login: "joel", password: "joel" } });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header:text('MitchellOp')");
    await insertText(".o-mail-Composer-input", "Hello MitchellOp!");
    await triggerHotkey("Enter");
    await contains(".o-mail-Message[data-persistent]:contains('Hello MitchellOp!')");
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button", { count: 2 });
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button[title='Fold']");
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button[title*='Close']");
    await contains(".o-discuss-Call", { count: 0 });
    // simulate operator starts call
    const [channelId] = pyEnv["discuss.channel"].search([
        ["channel_type", "=", "livechat"],
        [
            "channel_member_ids",
            "in",
            pyEnv["discuss.channel.member"].search([["partner_id", "=", joelPid]]),
        ],
    ]);
    await withUser(serverState.userId, () =>
        rpc("/mail/rtc/channel/join_call", { channel_id: channelId }, { silent: true })
    );
    await contains(".o-discuss-Call button", { count: 2 });
    await contains(".o-discuss-Call button[title='Join Video Call']");
    await contains(".o-discuss-Call button[title='Join Call']");
    // still same actions in header
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button", { count: 2 });
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button[title='Fold']");
    await contains(".o-mail-ChatWindow-header .o-mail-ActionList-button[title*='Close']");
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
            asyncStep(route);
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
    await waitForSteps(["/im_livechat/visitor_leave_session"]);
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
});

test("Should not show IM status of agents", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const joelUid = pyEnv["res.users"].create({
        name: "Joel",
        share: true,
        login: "joel",
        password: "joel",
    });
    pyEnv["res.partner"].create({ name: "Joel", user_ids: [joelUid] });
    pyEnv["res.partner"].write(serverState.partnerId, {
        im_status: "online",
        user_livechat_username: "MitchellOp",
    });
    await start({ authenticateAs: { login: "joel", password: "joel" } });
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header:text('MitchellOp')");
    await insertText(".o-mail-Composer-input", "Hello MitchellOp!");
    await triggerHotkey("Enter");
    await contains(".o-mail-Message[data-persistent]:contains('Hello MitchellOp!')");
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-ChatBubble");
    await assertChatBubbleAndWindowImStatus("MitchellOp", 0);
});
