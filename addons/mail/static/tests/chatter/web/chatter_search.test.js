import {
    SIZES,
    click,
    defineMailModels,
    editInput,
    insertText,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { contains, serverState } from "@web/../tests/web_test_helpers";

import { HIGHLIGHT_CLASS } from "@mail/core/common/message_search_hook";

describe.current.tags("desktop");
defineMailModels();

test("Chatter should display search icon", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.XXL });
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await waitFor("[title='Search Messages']:count(1)");
});

test("Click on the search icon should open the search form", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.XXL });
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await contains("[title='Search Messages']:count(1)").click();
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    await waitFor(".o-mail-SearchInput input:count(1)");
});

test("Search in chatter", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await waitFor(".o-mail-SearchMessageInput .o-mail-SearchInput input:count(1)");
    await editInput(document.body, ".o-mail-SearchInput input", "empty");
    await waitFor(".o-mail-SearchMessageResult .o-mail-Message:count(1)");
    await click(".o-mail-MessageCard-jump");
    await waitFor(
        ".o-mail-Message.o-highlighted .o-mail-Message-content:text('not empty'):count(1)"
    );
});

test("Close button should close the search panel", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Chatter-topbar [title='Search Messages']");
    await insertText(".o-mail-SearchInput input", "empty");
    await waitFor(".o-mail-SearchMessageResult .o-mail-Message:count(1)");
    await click(".o-mail-SearchMessageInput [title='Close']");
    await waitForNone(".o-mail-SearchMessageInput");
});

test("opening search in chatter hides files and pinned messages panels", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "Pinned message",
        model: "res.partner",
        pinned_at: "2025-01-01 00:00:00",
        res_id: partnerId,
    });
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "A.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button[aria-label='Attach files']:text('1'):count(1)").click();
    await waitFor(".o-mail-AttachmentBox:count(1)");
    await contains("[title='Search Messages']:count(1)").click();
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    await waitForNone(".o-mail-AttachmentBox");
    await waitFor("button[title='Attach files']:enabled:text('1'):count(1)");
    await contains("button[title='Pinned Messages']:enabled:count(1)").click();
    await waitFor(".o-mail-pinnedMessages:count(1)");
    await contains("[title='Search Messages']:count(1)").click();
    await waitFor(".o-mail-SearchMessageInput:count(1)");
    await waitForNone(".o-mail-pinnedMessages");
});

test("Search in chatter should be hightligted", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains("[title='Search Messages']:count(1)").click();
    await insertText(".o-mail-SearchInput input", "empty");
    await waitFor(`.o-mail-SearchMessageResult .o-mail-Message .${HIGHLIGHT_CLASS}:count(1)`);
});

test("Scrolling bottom in non-aside chatter should load more searched message", async () => {
    patchUiSize({ size: SIZES.LG }); // non-aside
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            author_id: serverState.partnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    await start();
    await openFormView("res.partner", partnerId);
    await contains("[title='Search Messages']:count(1)").click();
    await insertText(".o-mail-SearchInput input", "message");
    await waitFor(".o-mail-SearchMessageResult .o-mail-Message:count(30)");
    await scroll(".o_content", "bottom");
    await waitFor(".o-mail-SearchMessageResult .o-mail-Message:count(60)");
});

test("Switching chatter filters after empty result should show messages", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.message"].create({
        body: "not empty",
        message_type: "comment",
        model: "res.partner",
        res_id: serverState.partnerId,
        subtype_id: pyEnv["mail.message.subtype"].search([
            ["subtype_xmlid", "=", "mail.mt_comment"],
        ])[0],
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await contains("[title='Search Messages']:count(1)").click();
    await contains("[title='Filter Messages']:count(1)").click();
    await contains(".o-dropdown-item:text('Changes'):count(1)").click();
    await waitFor(".o-mail-MessageCardList:text('No messages found'):count(1)");
    await contains("[title='Filter Messages']:count(1)").click();
    await contains(".o-dropdown-item:text('Messages'):count(1)").click();
    await waitFor(".o-mail-SearchMessageResult .o-mail-Message-content:text('not empty'):count(1)");
});
