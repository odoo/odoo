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
import { Attachment } from "@mail/core/common/attachment_model";
import { describe, expect, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { asyncStep, patchWithCleanup, serverState, waitForSteps } from "@web/../tests/web_test_helpers";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { getOrigin } from "@web/core/utils/urls";
import { browser } from "@web/core/browser/browser";
import { session } from "@web/session";

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
        text: "Leaving will end the livechat. Proceed leaving?",
    });
    await triggerHotkey("Escape");
    await contains(".o-livechat-CloseConfirmation", { count: 0 });
    await triggerHotkey("Escape");
    await contains(".o-livechat-CloseConfirmation", {
        text: "Leaving will end the livechat. Proceed leaving?",
    });
    await triggerHotkey("Enter");
    await waitForSteps(["/im_livechat/visitor_leave_session"]);
    await contains(".o-mail-ChatWindow", { text: "Did we correctly answer your question?" });
});

test("should not make XMLHttpRequest to server file content when embedded externally", async () => {
    patchWithCleanup(browser.location, {
        origin: "https://www.hoot.test",
    });
    patchWithCleanup(session, {
        origin: window.location.origin,
    });
    mockFetch(() => {
        throw new Error("Should not fetch from external to odoo");
    });
    patchWithCleanup(HTMLAnchorElement.prototype, {
        click() {
            const url = new URL(this.href);
            expect.step(`${url.origin} ${url.searchParams.get("filename")}`);
        },
    });

    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();

    const [partnerUser] = pyEnv["res.users"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: partnerUser });
    await click(".o-livechat-LivechatButton");
    const textFile = new File(["hello, world"], "test.txt", { type: "text/plain" });
    await contains(".o-mail-Composer");

    await click(".o-mail-Composer button[title='More Actions']");
    await contains(".dropdown-item:contains('Attach files')");
    await inputFiles(".o-mail-Composer .o_input_file", [textFile]);
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(test.txt) .fa-check");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await contains(".o-mail-Message .o-mail-AttachmentContainer:contains(test.txt)");
    await click(".o-mail-Message .o-mail-AttachmentContainer:contains(test.txt) [title='Download']");

    expect.verifySteps([
        `${session.origin} test.txt`,
    ]);
});

/**
 * @see {@link import().ExternalLivechatDisabledPdfReason}
 */
test("should not allow preview of PDF attachments when embedded externally", async () => {
    patchWithCleanup(browser.location, {
        origin: "https://www.hoot.test",
    });
    patchWithCleanup(session, {
        origin: window.location.origin,
    });
    patchWithCleanup(Attachment.prototype, {
        get isViewable() {
            const res = super.isViewable;
            if (res) {
                expect.step("fileViewer.isViewable");
            }
            return res;
        },
    });

    const pyEnv = await startServer();
    await loadDefaultEmbedConfig();

    const [partnerUser] = pyEnv["res.users"].search_read([["id", "=", serverState.partnerId]]);
    await start({ authenticateAs: partnerUser });
    await click(".o-livechat-LivechatButton");
    const pdfFile = new File(["hello, world"], "test.pdf", { type: "application/pdf" });
    await contains(".o-mail-Composer");

    await click(".o-mail-Composer button[title='More Actions']");
    await contains(".dropdown-item:contains('Attach files')");
    await inputFiles(".o-mail-Composer .o_input_file", [pdfFile]);
    await contains(".o-mail-AttachmentContainer:not(.o-isUploading):contains(test.pdf) .fa-check");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await click(".o-mail-Message .o-mail-AttachmentContainer:contains(test.pdf)");
});
