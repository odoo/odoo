import { expect, test, getFixture } from "@odoo/hoot";
import { hover, waitFor, press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { helpers, registries, stores } from "@odoo/o-spreadsheet";
import { selectCell } from "@spreadsheet/../tests/helpers/commands";
import { getActionMenu } from "@spreadsheet/../tests/helpers/ui";
import { defineTestSpreadsheetEditionModels } from "@test_spreadsheet_edition/../tests/helpers/data";
import { createThread, setupWithThreads } from "@test_spreadsheet_edition/../tests/helpers/helpers";
import { contains, preloadBundle } from "@web/../tests/web_test_helpers";

defineTestSpreadsheetEditionModels();
preloadBundle("web.assets_emoji");

const { topbarMenuRegistry } = registries;
const { HoveredCellStore } = stores;

const { toCartesian } = helpers;

test("Hover cell only shows messages, Composer appears on click", async () => {
    const { model, pyEnv, env } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);

    env.getStore(HoveredCellStore).hover({ col: 0, row: 1 });
    await animationFrame();

    expect(".o-thread-popover .o-mail-Thread").toHaveCount(1);
    expect(".o-thread-popover .o-mail-Composer").toHaveCount(0);

    await contains("div.o-thread-popover [tabindex]").focus();
    await animationFrame();
    expect(".o-mail-Thread").toHaveCount(1);
    expect(".o-mail-Composer").toHaveCount(1);
});

test("Composer is not focused when navigating cells with keyboard", async () => {
    const { model, pyEnv } = await setupWithThreads();
    const parent = getFixture();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);

    selectCell(model, "A1");
    await animationFrame();

    await press("arrowdown");
    await animationFrame();

    expect(".o-thread-popover").toHaveCount(1);
    expect(".o-mail-Thread").toHaveCount(1);
    expect(".o-mail-Composer").toHaveCount(1);

    const mailComposerInput = parent.querySelector(".o-mail-Composer textarea");
    expect(document.activeElement).not.toBe(mailComposerInput);

    await press("arrowdown");
    await animationFrame();

    expect(model.getters.getActivePosition()).toEqual({ col: 0, row: 2, sheetId: "Sheet1" });
});

test("Selecting the cell with a resolved thread does not open the thread popover", async () => {
    const { model, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, col: 0, row: 0 }, ["wave"]);
    const threadId = model.getters.getSpreadsheetThreads([sheetId])[0].threadId;
    model.dispatch("EDIT_COMMENT_THREAD", { threadId, sheetId, col: 0, row: 0, isResolved: true });
    selectCell(model, "A1");
    await animationFrame();
    expect(".o-thread-popover").toHaveCount(0);
    expect(".o-mail-Thread").toHaveCount(0);
});

test("Send messages from the popover", async () => {
    const { model, env } = await setupWithThreads();
    selectCell(model, "A2");
    const action = await getActionMenu(topbarMenuRegistry, ["insert", "insert_comment"], env);
    expect(action.isVisible(env)).toBe(true);
    await action.execute(env);
    await animationFrame();

    expect(".o-mail-Composer textarea:first").toBeFocused();

    await contains(".o-mail-Composer textarea").edit("msg1", { confirm: false });
    await contains(".o-mail-Composer textarea").press("Enter", { ctrlKey: true });
    await waitFor(".o-mail-Message", { timeout: 500, visible: false });
    let threadIds = model.getters.getCellThreads(model.getters.getActivePosition());
    expect(threadIds).toEqual([{ threadId: 1, isResolved: false }]);
    expect(".o-mail-Message").toHaveCount(1);

    await contains(".o-mail-Composer textarea", { visible: false }).edit("msg2");
    await animationFrame();
    await contains(".o-mail-Composer-send:enabled").click();
    expect(".o-mail-Message").toHaveCount(2);

    threadIds = model.getters.getCellThreads(model.getters.getActivePosition());
    expect(threadIds).toEqual([{ threadId: 1, isResolved: false }]);
    expect(".o-mail-Message").toHaveCount(2);
});

test("Open side panel from thread popover", async () => {
    const { model, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    selectCell(model, "A2");
    await animationFrame();
    await contains(".o-thread-popover div.o-thread-highlight button").click();
    expect(".o-threads-side-panel").toHaveCount(1);
});

test.tags("desktop");
test("edit comment from the thread popover", async () => {
    const { model, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    selectCell(model, "A2");
    await hover(waitFor(".o-mail-Message"));
    await contains(".o-mail-Message [title='Expand']").click();
    await contains(".dropdown-item:contains(Edit)").click();
    await contains(".o-mail-Composer textarea").edit("msg1", { confirm: false });
    await contains(".o-mail-Composer textarea").press("Enter");
    await waitFor(".o-mail-Message-content:contains(msg1 (edited))");
    expect(".o-mail-Message-content").toHaveText("msg1 (edited)");
});

test.tags("desktop");
test("Upload button is not visible for spreadsheet cell threads", async () => {
    const { model, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    selectCell(model, "A2");
    await hover(waitFor(".o-mail-Message"));
    expect(".o-mail-Composer .o_input_file").toHaveCount(0);
    await contains(".o-mail-Message [title='Expand']").click();
    await contains(".o-mail-Message-moreMenu [title='Edit']").click();
    expect(".o-mail-Message .o_input_file").toHaveCount(0);
});
