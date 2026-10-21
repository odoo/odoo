import { describe, expect, queryAll, queryAllAttributes, queryAllTexts, test } from "@odoo/hoot";
import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { location } from "@web/core/browser/browser";
import { session } from "@web/session";
import { pointerState } from "@web_tuto/pointer/pointer_state";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

describe.current.tags("desktop");

function getTutorials() {
    return [
        {
            id: 1,
            title: "Partners",
            state: "running",
            chapters: [[true, true], [true, false, false], [false]],
        },
        { id: 2, title: "Contracts", state: "done", chapters: [[true]] },
        { id: 3, title: "Notes", state: "new", chapters: [[false], [false]] },
    ];
}

async function openTutorialsDialog() {
    await mountWithCleanup(UserMenu);
    await contains("button.o_user_menu").click();
    await contains("[data-menu=tutorials]").click();
}

test("the tutorials are listed below the help in the user menu", async () => {
    onRpc("web_tuto.tutorial", "get_user_tutorials", getTutorials);
    await mountWithCleanup(UserMenu);
    await contains("button.o_user_menu").click();
    const items = queryAllAttributes(".dropdown-menu .dropdown-item", "data-menu");
    expect(items.indexOf("tutorials")).toBe(items.indexOf("support") + 1);
});

test("the tutorials dialog shows their progress by chapter and step", async () => {
    patchWithCleanup(session, { tutorial_enabled: true });
    onRpc("web_tuto.tutorial", "get_user_tutorials", getTutorials);
    await openTutorialsDialog();
    expect(queryAllTexts(".o_tutorials_row .fw-bold")).toEqual(["Partners", "Contracts", "Notes"]);
    expect(queryAllTexts(".o_tutorials_progress")).toEqual([
        "In progress · 3/6 steps",
        "Done · 1/1 steps",
        "Not started · 0/2 steps",
    ]);
    expect(queryAllTexts(".o_tutorials_play")).toEqual(["Resume", "Replay", "Play"]);
    expect(
        queryAll(".o_tutorials_row:first .o_tutorials_chapter").map(
            (chapter) => chapter.querySelectorAll(".o_tutorials_step.o_done").length
        )
    ).toEqual([2, 1, 0]);
    expect(".o_tutorials_switch input").toBeChecked();
});

test("a tutorial is played, or restarted or marked as done from its dropdown", async () => {
    onRpc("web_tuto.tutorial", "get_user_tutorials", getTutorials);
    for (const method of ["action_resume", "action_restart", "mark_done"]) {
        onRpc("web_tuto.tutorial", method, ({ args }) => {
            expect.step(`${method} ${args[0]}`);
            return { type: "ir.actions.act_window_close" };
        });
    }
    await openTutorialsDialog();
    expect(".o_tutorials_row:eq(1) .o_tutorials_toggle").toHaveCount(0);
    await contains(".o_tutorials_row:eq(0) .o_tutorials_toggle").click();
    expect(queryAllTexts(".o-dropdown--menu .dropdown-item")).toEqual(["Restart", "Mark as done"]);
    await contains(".o_tutorials_row:eq(2) .o_tutorials_toggle").click();
    expect(queryAllTexts(".o-dropdown--menu .dropdown-item")).toEqual(["Mark as done"]);

    await contains(".o_tutorials_row:eq(0) .o_tutorials_play").click();
    expect.verifySteps(["action_resume 1"]);
    await contains(".o_tutorials_row:eq(0) .o_tutorials_toggle").click();
    await contains(".o_tutorials_restart").click();
    expect.verifySteps(["action_restart 1"]);
    await contains(".o_tutorials_row:eq(2) .o_tutorials_play").click();
    expect.verifySteps(["action_restart 3"]);
    await contains(".o_tutorials_row:eq(2) .o_tutorials_toggle").click();
    await contains(".o_tutorials_mark_done").click();
    expect.verifySteps(["mark_done 3"]);
    expect(".o_tutorials_row:eq(2) .o_tutorials_progress").toHaveText("Done · 2/2 steps");
    expect(".o_tutorials_row:eq(2) .o_tutorials_play").toHaveText("Replay");
    expect(".o_tutorials_row:eq(2) .o_tutorials_toggle").toHaveCount(0);
});

test("the tips are always shown once switched in the dialog", async () => {
    patchWithCleanup(session, { tutorial_tips_shown: false });
    patchWithCleanup(pointerState, { tipsShown: false });
    onRpc("web_tuto.tutorial", "get_user_tutorials", getTutorials);
    onRpc("res.users", "write", ({ args }) => {
        expect.step(`write ${JSON.stringify(args)}`);
        return true;
    });
    await openTutorialsDialog();
    expect(".o_tutorials_tips_switch input").not.toBeChecked();
    await contains(".o_tutorials_tips_switch input").click();
    expect.verifySteps([`write [[${serverState.userId}],{"tutorial_tips_shown":true}]`]);
    expect(".o_tutorials_tips_switch input").toBeChecked();
    expect(pointerState.tipsShown).toBe(true);
});

test("the tutorials are switched in the dialog", async () => {
    patchWithCleanup(session, { tutorial_enabled: true });
    patchWithCleanup(location, {
        reload() {
            expect.step("reload");
        },
    });
    onRpc("web_tuto.tutorial", "get_user_tutorials", getTutorials);
    onRpc("res.users", "write", ({ args }) => {
        expect.step(`write ${JSON.stringify(args)}`);
        return true;
    });
    await openTutorialsDialog();
    await contains(".o_tutorials_switch input").click();
    expect.verifySteps([`write [[${serverState.userId}],{"tutorial_enabled":false}]`, "reload"]);
});
