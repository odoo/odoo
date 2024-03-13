import { describe, test } from "@odoo/hoot";
import { HIGHLIGHT_CLASS } from "@mail/core/common/message_search_hook";
import {
    SIZES,
    click,
    contains,
    defineMailModels,
    insertText,
    openFormView,
    patchUiSize,
    scroll,
    start,
    startServer,
    triggerHotkey,
} from "../../mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Chatter should display search icon", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.XXL });
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await contains("[title='Search Messages']");
});

test("Click on the search icon should open the search form", async () => {
    const pyEnv = await startServer();
    patchUiSize({ size: SIZES.XXL });
    await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await contains(".o_searchview");
    await contains(".o_searchview_input");
});

test("Click again on the search icon should close the search form", async () => {
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
    await contains(".o_searchview");
    await click(".o-mail-Chatter-topbar [title='Search Messages']");
    await contains(".o_searchview", { count: 0 });
    await contains(".o_searchview_input", { count: 0 });
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
    await insertText(".o_searchview_input", "empty");
    triggerHotkey("Enter");
    await contains(".o-mail-Chatter-search .o-mail-Message");
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
    await insertText(".o_searchview_input", "empty");
    triggerHotkey("Enter");
    await contains(".o-mail-Chatter-search .o-mail-Message");
    await click(".o-mail-Chatter-topbar [title='Search Messages']");
    await contains(".o-mail-Chatter-search", { count: 0 });
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
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "empty");
    triggerHotkey("Enter");
    await contains(`.o-mail-Chatter-search .o-mail-Message .${HIGHLIGHT_CLASS}`);
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
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-Chatter-search .o-mail-Message", { count: 30 });
    await scroll(".o_content", "bottom");
    await contains(".o-mail-Chatter-search .o-mail-Message", { count: 60 });
});
