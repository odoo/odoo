import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { helpers, registries } from "@odoo/o-spreadsheet";
import { getActionMenu } from "@spreadsheet/../tests/helpers/ui";
import { CommentsStore } from "@spreadsheet_edition/bundle/comments/comments_store";
import { defineTestSpreadsheetEditionModels } from "@test_spreadsheet_edition/../tests/helpers/data";
import { createThread, setupWithThreads } from "@test_spreadsheet_edition/../tests/helpers/helpers";

const { cellMenuRegistry, topbarMenuRegistry } = registries;
const { toCartesian } = helpers;

defineTestSpreadsheetEditionModels();

test("visibility menu", async () => {
    const { model, env } = await setupWithThreads();
    const action = await getActionMenu(topbarMenuRegistry, ["view", "show", "show_comments"], env);
    expect(action.isActive(env)).toBe(true);
    const commentsStore = env.getStore(CommentsStore);
    commentsStore.toggleComments();
    model.dispatch("TOGGLE_COMMENTS");
    expect(action.isActive(env)).toBe(false);
});

test("Insert thread topbar menu", async () => {
    const { env } = await setupWithThreads();
    const action = await getActionMenu(topbarMenuRegistry, ["insert", "insert_comment"], env);
    expect(action.isVisible(env)).toBe(true);
    await action.execute(env);
    await animationFrame();
    expect(".o-thread-popover").toHaveCount(1);
    expect(".o-mail-Thread").toHaveCount(0);
    expect(".o-mail-Composer").toHaveCount(1);
    expect(".o-mail-Composer textarea:first").toBeFocused();
});

test("Open sidepanel from topbar menu", async () => {
    const { model, pyEnv, env } = await setupWithThreads();
    const action = await getActionMenu(topbarMenuRegistry, ["view", "view_comments"], env);
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    await action.execute(env);
    await animationFrame();
    expect(".o-threads-side-panel").toHaveCount(1);
    expect(".o-threads-side-panel .o-thread-item").toHaveCount(1);
});

test("Start a thread from cell menu", async () => {
    const { env } = await setupWithThreads();
    const action = await getActionMenu(cellMenuRegistry, ["insert_comment"], env);
    expect(action.isVisible(env)).toBe(true);
    await action.execute(env);
    await animationFrame();
    expect(".o-thread-popover").toHaveCount(1);
    expect(".o-mail-Thread").toHaveCount(0);
    expect(".o-mail-Composer").toHaveCount(1);
    expect(".o-thread-popover .o-mail-Composer textarea:first").toBeFocused();
});

test("Jump to an existing thread from the cell menu", async () => {
    const { model, env, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("B2") }, ["wave"]);
    const action = await getActionMenu(cellMenuRegistry, ["insert_comment"], env);
    // invisible on cell with a thread
    model.selection.selectCell(1, 1);
    expect(action.isVisible(env)).toBe(true);
});
