/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { start } from "@mail/../tests/helpers/test_utils";
import { SIZES, patchUiSize } from "../helpers/patch_ui_size";
import { triggerHotkey } from "@web/../tests/helpers/utils";
import { click, contains, insertText, scroll } from "@web/../tests/utils";
import { HIGHLIGHT_CLASS } from "@mail/core/common/message_search_hook";

QUnit.module("chatter search");

QUnit.test("Chatter should display search icon", async () => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await contains("[title='Search Messages']");
});

QUnit.test("Click on the search icon should open the search form", async () => {
    patchUiSize({ size: SIZES.XXL });
    const { openFormView, pyEnv } = await start();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await contains(".o_searchview");
    await contains(".o_searchview_input");
});

QUnit.test("Click again on the search icon should close the search form", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Chatter-topbar [title='Search Messages']");
    await contains(".o_searchview");
    await click(".o-mail-Chatter-topbar [title='Search Messages']");
    await contains(".o_searchview", { count: 0 });
    await contains(".o_searchview_input", { count: 0 });
});

QUnit.test("Search in chatter", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "empty");
    triggerHotkey("Enter");
    await contains(".o-mail-Chatter-search .o-mail-Message");
});

QUnit.test("Close button should close the search panel", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Chatter-topbar [title='Search Messages']");
    await insertText(".o_searchview_input", "empty");
    triggerHotkey("Enter");
    await contains(".o-mail-Chatter-search .o-mail-Message");
    await click(".o-mail-Chatter-topbar [title='Search Messages']");
    await contains(".o-mail-Chatter-search", { count: 0 });
});

QUnit.test("Search in chatter should be hightligted", async () => {
    patchUiSize({ size: SIZES.XXL });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    pyEnv["mail.message"].create({
        body: "not empty",
        model: "res.partner",
        res_id: partnerId,
    });
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "empty");
    triggerHotkey("Enter");
    await contains(`.o-mail-Chatter-search .o-mail-Message .${HIGHLIGHT_CLASS}`);
});

QUnit.test("Scrolling bottom in non-aside chatter should load more searched message", async () => {
    patchUiSize({ size: SIZES.LG }); // non-aside
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "John Doe" });
    for (let i = 0; i < 60; i++) {
        pyEnv["mail.message"].create({
            author_id: pyEnv.currentPartnerId,
            body: "This is a message",
            attachment_ids: [],
            message_type: "comment",
            model: "res.partner",
            res_id: partnerId,
        });
    }
    const { openFormView } = await start();
    await openFormView("res.partner", partnerId);
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "message");
    triggerHotkey("Enter");
    await contains(".o-mail-Chatter-search .o-mail-Message", { count: 30 });
    await scroll(".o_content", "bottom");
    await contains(".o-mail-Chatter-search .o-mail-Message", { count: 60 });
});
