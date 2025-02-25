import { LivechatButton } from "@im_livechat/embed/common/livechat_button";
import {
    defineLivechatModels,
    loadDefaultEmbedConfig,
} from "@im_livechat/../tests/livechat_test_helpers";
import { describe, test } from "@odoo/hoot";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { getOrigin } from "@web/core/utils/urls";
import {
    Command,
    mountWithCleanup,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import {
    assertSteps,
    click,
    contains,
    inputFiles,
    insertText,
    onRpcBefore,
    patchUiSize,
    SIZES,
    start,
    startServer,
    step,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { expirableStorage } from "@im_livechat/embed/common/expirable_storage";

describe.current.tags("desktop");
defineLivechatModels();

test("do not save fold state of temporary live chats", async () => {
    patchWithCleanup(LivechatButton, { DEBOUNCE_DELAY: 0 });
    await startServer();
    await loadDefaultEmbedConfig();
    onRpcBefore("/discuss/channel/fold", (args) => {
        step(`fold - ${args.state}`);
    });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await insertText(".o-mail-Composer-input", "Hello");
    await triggerHotkey("Enter");
    await contains(".o-mail-Message", { text: "Hello" });
    await click(".o-mail-ChatWindow-header");
    await contains(".o-mail-Message", { text: "Hello", count: 0 });
    await assertSteps(["fold - folded"]);
    await click(".o-mail-ChatBubble");
    await click("[title*='Close Chat Window']");
    await assertSteps(["fold - open"]); // clicking close shows the feedback panel
    await click(".o-livechat-CloseConfirmation-leave");
    await click("button", { text: "Close conversation" });
    await assertSteps(["fold - closed"]);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-Message", { text: "Hello, how may I help you?" });
    await assertSteps([]);
    await click(".o-mail-ChatWindow-header");
    await assertSteps([]);
});

test("internal users can upload file to temporary thread", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    const [partnerUser] = pyEnv["res.users"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: partnerUser });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    const file = new File(["hello, world"], "text.txt", { type: "text/plain" });
    await contains(".o-mail-Composer");
    await contains("button[title='Attach files']");
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [file]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });
    await triggerHotkey("Enter");
    await contains(".o-mail-Message .o-mail-AttachmentCard", { text: "text.txt" });
});

test("Conversation name is operator livechat user name", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
    await click(".o-livechat-LivechatButton");
    await contains(".o-mail-ChatWindow-header", { text: "MitchellOp" });
});

test("avatar url contains access token for non-internal users", async () => {
    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();
    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    const [partner] = pyEnv["res.partner"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: false });
    await mountWithCleanup(LivechatButton);
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

test("livechat is shown as bubble on page reload", async () => {
    const pyEnv = await startServer();
    const livechatChannelId = await loadDefaultEmbedConfig();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId, fold_state: "open" }),
        ],
        channel_type: "livechat",
        livechat_active: true,
        livechat_channel_id: livechatChannelId,
        livechat_operator_id: serverState.partnerId,
    });
    expirableStorage.setItem(
        "im_livechat.saved_state",
        JSON.stringify({
            store: { "discuss.channel": [{ id: channelId }] },
            persisted: true,
            livechatUserId: serverState.publicUserId,
        })
    );

    pyEnv["res.partner"].write(serverState.partnerId, { user_livechat_username: "MitchellOp" });
    patchUiSize({ size: SIZES.SM });
    await start({
        authenticateAs: { ...pyEnv["mail.guest"].read(guestId)[0], _name: "mail.guest" },
    });
    await click(".o-mail-ChatBubble");
    await contains(".o-mail-ChatWindow-header", { text: "MitchellOp" });
});
