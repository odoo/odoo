import { Component, onWillStart, proxy, t, usePlugin, useProps } from "@odoo/owl";
import { location } from "@web/core/browser/browser";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { ORM } from "@web/core/orm_plugin";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { session } from "@web/session";
import { getStepKeys, TutorialPlugin } from "@web_tuto/plugin";
import { pointerState } from "@web_tuto/pointer/pointer_state";

/**
 * @param {TutorialChapterDefinition[]} chapters
 * @param {string[]} doneSteps the keys of the steps the user did
 * @param {boolean} isDone whether the user finished the tutorial
 * @returns {boolean[][]} whether each step is shown as done, by chapter: the
 *   steps up to the last done one, all of them once finished
 */
function getStepsDoneByChapter(chapters, doneSteps, isDone) {
    const stepKeys = getStepKeys(chapters);
    const keys = stepKeys.flat();
    const shownDoneCount = isDone
        ? keys.length
        : keys.findLastIndex((key) => doneSteps.includes(key)) + 1;
    let index = 0;
    return stepKeys.map((chapterKeys) => chapterKeys.map(() => index++ < shownDoneCount));
}

/**
 * The tutorials of the user with their progress (the ones of the registry
 * "web_tuto.tutorials"), and the switches of the tutorials and their tips
 */
export class TutorialsDialog extends Component {
    static buttonLabels = {
        done: _t("Replay"),
        new: _t("Play"),
        running: _t("Resume"),
    };
    static components = { CheckBox, Dialog, Dropdown, DropdownItem };
    static stateLabels = {
        done: _t("Done"),
        new: _t("Not started"),
        running: _t("In progress"),
    };
    static template = "web_tuto.TutorialsDialog";

    action = useService("action");
    orm = usePlugin(ORM);
    props = useProps({ close: t.function() });
    tutorialPlugin = usePlugin(TutorialPlugin);
    tutorialsEnabled = Boolean(session.tutorial_enabled);

    setup() {
        this.state = proxy({
            tipsShown: Boolean(session.tutorial_tips_shown),
            tutorials: [],
        });
        onWillStart(async () => {
            const definitions = registry.category("web_tuto.tutorials");
            const tutorials = await this.orm.call("web_tuto.tutorial", "get_user_tutorials");
            this.state.tutorials = tutorials
                .filter(({ name }) => definitions.contains(name))
                .map((tutorial) => ({
                    ...tutorial,
                    stepsDoneByChapter: getStepsDoneByChapter(
                        definitions.get(tutorial.name),
                        tutorial.done_steps,
                        tutorial.state === "done"
                    ),
                }));
        });
    }

    /**
     * @param {Object} tutorial
     * @returns {string} its done steps out of all of them, e.g. "3/13 steps"
     */
    getProgress(tutorial) {
        const steps = tutorial.stepsDoneByChapter.flat();
        return _t("%(done)s/%(total)s steps", {
            done: steps.filter(Boolean).length,
            total: steps.length,
        });
    }

    /**
     * Ends the tutorial for the user, stopping it if it runs in the page
     * @param {Object} tutorial
     */
    async onMarkDone(tutorial) {
        const running = this.tutorialPlugin.tutorials.find(({ id }) => id === tutorial.id);
        if (running) {
            this.tutorialPlugin.endTutorial(running);
        } else {
            await this.orm.call("web_tuto.tutorial", "mark_done", [[tutorial.id]]);
        }
        tutorial.state = "done";
        tutorial.stepsDoneByChapter = tutorial.stepsDoneByChapter.map((chapter) =>
            chapter.map(() => true)
        );
    }

    /**
     * Resumes the tutorial in progress, plays the other ones from scratch
     * @param {Object} tutorial
     */
    async onPlay(tutorial) {
        const method = tutorial.state === "running" ? "action_resume" : "action_restart";
        await this._runTutorial(tutorial, method);
    }

    /**
     * Plays the tutorial in progress from scratch
     * @param {Object} tutorial
     */
    async onRestart(tutorial) {
        await this._runTutorial(tutorial, "action_restart");
    }

    /** Always shows the tips, or only while hovering them */
    async onSwitchTips() {
        const tipsShown = !this.state.tipsShown;
        await this.orm.write("res.users", [user.userId], {
            tutorial_tips_shown: tipsShown,
        });
        this.state.tipsShown = tipsShown;
        session.tutorial_tips_shown = tipsShown;
        pointerState.tipsShown = tipsShown;
    }

    /** Enables or disables the tutorials, reloading the page to apply it */
    async onSwitchTutorials() {
        await this.orm.write("res.users", [user.userId], {
            tutorial_enabled: !this.tutorialsEnabled,
        });
        location.reload();
    }

    /**
     * @param {Object} tutorial
     * @param {"action_resume"|"action_restart"} method
     * @private
     */
    async _runTutorial(tutorial, method) {
        const action = await this.orm.call("web_tuto.tutorial", method, [[tutorial.id]]);
        await this.action.doAction(action);
    }
}

function tutorialsItem() {
    const dialog = useService("dialog");
    return {
        type: "item",
        id: "tutorials",
        description: _t("Tutorials"),
        callback: () => dialog.add(TutorialsDialog),
        sequence: 21,
    };
}

registry.category("user_menuitems").add("tutorials", tutorialsItem);
