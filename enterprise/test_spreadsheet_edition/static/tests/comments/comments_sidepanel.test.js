import { beforeEach, describe, expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { helpers, stores } from "@odoo/o-spreadsheet";
import { CommentsStore } from "@spreadsheet_edition/bundle/comments/comments_store";
import { defineTestSpreadsheetEditionModels } from "@test_spreadsheet_edition/../tests/helpers/data";
import { createThread, setupWithThreads } from "@test_spreadsheet_edition/../tests/helpers/helpers";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineTestSpreadsheetEditionModels();

const { CellPopoverStore } = stores;

const { toCartesian, toZone } = helpers;

let fixture;
beforeEach(() => {
    fixture = getFixture();
});

test("Selected thread is highlighted in the side panel", async () => {
    const { model, env, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A3") }, ["wave"]);

    env.openSidePanel("Comments");
    await animationFrame();

    expect(".o-threads-side-panel").toHaveCount(1);
    expect(".o-threads-side-panel .o-thread-item").toHaveCount(2);
});

test("Side panel filter 'active sheet'/'all sheets'", async () => {
    const { model, env, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    const sheetId2 = "sh2";
    model.dispatch("CREATE_SHEET", { sheetId: sheetId2, position: 1 });
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A3") }, ["wave"]);
    await createThread(model, pyEnv, { sheetId: sheetId2, ...toCartesian("A3") }, ["wave"]);

    env.openSidePanel("Comments");
    await animationFrame();
    expect(".o-threads-side-panel .o-thread-item").toHaveCount(3);
    await contains(".o-threads-side-panel select").select("activeSheet");
    expect(".o-threads-side-panel .o-thread-item").toHaveCount(2);
    model.dispatch("ACTIVATE_SHEET", { sheetIdTo: sheetId2, sheetIdFrom: sheetId });
    await animationFrame();
    expect(".o-threads-side-panel .o-thread-item").toHaveCount(1);
});

test("click on a thread in the side panel selects it in the grid", async () => {
    const { model, env, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    env.openSidePanel("Comments");
    await animationFrame();
    expect(model.getters.getSelectedZone()).toEqual(toZone("A1"));
    await contains(".o-threads-side-panel .o-thread-item").click();
    expect(model.getters.getSelectedZone()).toEqual(toZone("A2"));
});

test("click on a thread in the side panel makes threads visible", async () => {
    const { model, env, pyEnv } = await setupWithThreads();
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    const commentsStore = env.getStore(CommentsStore);
    env.openSidePanel("Comments");
    await animationFrame();
    expect(commentsStore.areCommentsActive).toBe(true);
    commentsStore.toggleComments();
    expect(commentsStore.areCommentsActive).toBe(false);
    await contains(".o-threads-side-panel .o-thread-item").click();
    expect(commentsStore.areCommentsActive).toBe(true);
});

test("Side panel does not close if visibility is off", async () => {
    const { model, env, pyEnv } = await setupWithThreads();
    const commentsStore = env.getStore(CommentsStore);
    const sheetId = model.getters.getActiveSheetId();
    await createThread(model, pyEnv, { sheetId, ...toCartesian("A2") }, ["wave"]);
    env.openSidePanel("Comments");
    await animationFrame();
    expect(".o-threads-side-panel").toHaveCount(1);
    commentsStore.toggleComments();
    await animationFrame();
    expect(".o-threads-side-panel").toHaveCount(1);
});

test("Resolve/Re-open thread from the side panel", async () => {
    const { model, env, pyEnv } = await setupWithThreads();
    const popoverStore = env.getStore(CellPopoverStore);
    const sheetId = model.getters.getActiveSheetId();
    const cellPosition = { sheetId, ...toCartesian("A2") };
    await createThread(model, pyEnv, cellPosition, ["wave"]);
    env.openSidePanel("Comments");
    await animationFrame();
    const thread = fixture.querySelector(".o-sidePanel .o-thread-item");
    await contains(thread).click();
    expect(popoverStore.persistentCellPopover).toEqual({
        isOpen: true,
        col: 0,
        row: 1,
        sheetId: "Sheet1",
        type: "OdooCellComment",
    });
    await contains(thread.querySelector("span.thread-menu")).click();
    let menuItems = fixture.querySelectorAll(".o-menu .o-menu-item");
    await contains(menuItems[0]).click();
    let threadIds = model.getters.getCellThreads(cellPosition);
    expect(threadIds).toEqual([{ threadId: 1, isResolved: true }]);
    expect(".o-sidePanel .o-thread-item span.resolved").toHaveCount(1);
    expect(popoverStore.persistentCellPopover).toEqual({ isOpen: false });

    await contains(thread.querySelector("span.thread-menu")).click();
    menuItems = fixture.querySelectorAll(".o-menu .o-menu-item");
    await contains(menuItems[0]).click();
    threadIds = model.getters.getCellThreads(cellPosition);
    expect(threadIds).toEqual([{ threadId: 1, isResolved: false }]);
    expect(".o-sidePanel .o-thread-item span.resolved").toHaveCount(0);
    expect(popoverStore.persistentCellPopover).toEqual({
        isOpen: true,
        col: 0,
        row: 1,
        sheetId: "Sheet1",
        type: "OdooCellComment",
    });
});
