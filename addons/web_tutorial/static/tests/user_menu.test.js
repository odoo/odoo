import {
    beforeEach,
    describe,
    expect,
    queryAll,
    queryAllAttributes,
    queryAllTexts,
    test,
} from "@odoo/hoot";
import {
    contains,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
} from "@web/../tests/web_test_helpers";
import { location } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { pointerState } from "@web_tutorial/pointer/pointer_state";

describe.current.tags("desktop");

/**
 * @param {string} model
 * @param {...number} stepCounts the number of steps of each chapter
 * @returns {TutorialChapterDefinition[]} chapters of form views, with their
 *   fields "field_1", "field_2", etc.
 */
function getChapters(model, ...stepCounts) {
    return stepCounts.map((stepCount) => ({
        model,
        steps: Array.from({ length: stepCount }, (_, index) => ({
            content: "Fill it",
            name: `field_${index + 1}`,
            type: "field",
        })),
        viewType: "form",
    }));
}

function getTutorials() {
    return [
        {
            done_steps: ["partner,form,field_1", "partner,form,field_1,2"],
            id: 1,
            name: "partner_tutorial",
            state: "running",
            title: "Partners",
        },
        {
            done_steps: [],
            id: 2,
            name: "contract_tutorial",
            state: "done",
            title: "Contracts",
        },
        {
            done_steps: [],
            id: 3,
            name: "note_tutorial",
            state: "new",
            title: "Notes",
        },
        {
            done_steps: [],
            id: 4,
            name: "uninstalled_tutorial",
            state: "new",
            title: "Uninstalled",
        },
    ];
}

beforeEach(() => {
    registry
        .category("web_tutorial.tutorials")
        .add("partner_tutorial", getChapters("partner", 2, 3, 1))
        .add("contract_tutorial", getChapters("contract", 1))
        .add("note_tutorial", getChapters("note", 1, 1));
});

async function openTutorialsDialog() {
    await mountWithCleanup(UserMenu);
    await contains("button.o_user_menu").click();
    await contains("[data-menu=tutorials]").click();
}

test("the tutorials are listed below the help in the user menu", async () => {
    onRpc("web_tutorial.tutorial", "get_user_tutorials", getTutorials);
    await mountWithCleanup(UserMenu);
    await contains("button.o_user_menu").click();
    const items = queryAllAttributes(".dropdown-menu .dropdown-item", "data-menu");
    expect(items.indexOf("tutorials")).toBe(items.indexOf("support") + 1);
});

test("the tutorials are hidden from the user menu when no app has any", async () => {
    const tutorials = registry.category("web_tutorial.tutorials");
    for (const [name] of tutorials.getEntries()) {
        tutorials.remove(name);
    }
    await mountWithCleanup(UserMenu);
    await contains("button.o_user_menu").click();
    expect("[data-menu=tutorials]").toHaveCount(0);
});

test("the tutorials dialog shows the progress of the tutorials of the registry, by chapter and step", async () => {
    patchWithCleanup(session, { tutorial_enabled: true });
    onRpc("web_tutorial.tutorial", "get_user_tutorials", getTutorials);
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
    onRpc("web_tutorial.tutorial", "get_user_tutorials", getTutorials);
    for (const method of ["action_resume", "action_restart", "mark_done"]) {
        onRpc("web_tutorial.tutorial", method, ({ args }) => {
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
    onRpc("web_tutorial.tutorial", "get_user_tutorials", getTutorials);
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
    onRpc("web_tutorial.tutorial", "get_user_tutorials", getTutorials);
    onRpc("res.users", "write", ({ args }) => {
        expect.step(`write ${JSON.stringify(args)}`);
        return true;
    });
    await openTutorialsDialog();
    await contains(".o_tutorials_switch input").click();
    expect.verifySteps([`write [[${serverState.userId}],{"tutorial_enabled":false}]`, "reload"]);
});
