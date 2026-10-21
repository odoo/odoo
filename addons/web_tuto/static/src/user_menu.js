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
import { TutorialPlugin } from "@web_tuto/plugin";
import { pointerState } from "@web_tuto/pointer/pointer_state";

/**
 * The tutorials the user can go through, with their progress by chapter, to
 * play, resume, replay, restart or mark them as done; and the switches enabling
 * or disabling them, and always showing their tips
 */
export class TutorialsDialog extends Component {
    static template = "web_tuto.TutorialsDialog";
    static components = { CheckBox, Dialog, Dropdown, DropdownItem };
    props = useProps({ close: t.function() });

    static stateLabels = {
        new: _t("Not started"),
        running: _t("In progress"),
        done: _t("Done"),
    };
    static buttonLabels = {
        new: _t("Play"),
        running: _t("Resume"),
        done: _t("Replay"),
    };

    orm = usePlugin(ORM);
    tutorialPlugin = usePlugin(TutorialPlugin);
    action = useService("action");
    tutorialsEnabled = Boolean(session.tutorial_enabled);

    setup() {
        this.state = proxy({ tutorials: [], tipsShown: Boolean(session.tutorial_tips_shown) });
        onWillStart(async () => {
            this.state.tutorials = await this.orm.call("web_tuto.tutorial", "get_user_tutorials");
        });
    }

    /**
     * @param {Object} tutorial
     * @returns {string} its done steps out of all of them, e.g. "3/13 steps"
     */
    getProgress(tutorial) {
        const steps = tutorial.chapters.flat();
        return _t("%(done)s/%(total)s steps", {
            done: steps.filter(Boolean).length,
            total: steps.length,
        });
    }

    /**
     * Plays a tutorial not started yet or done from scratch, or resumes the
     * one in progress
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

    /**
     * Ends the tutorial for the user, stopping it if it runs in the page
     * @param {Object} tutorial
     */
    async onMarkDone(tutorial) {
        const running = this.tutorialPlugin.tutorials.find((t) => t.id === tutorial.id);
        if (running) {
            this.tutorialPlugin.endTutorial(running);
        } else {
            await this.orm.call("web_tuto.tutorial", "mark_done", [[tutorial.id]]);
        }
        tutorial.state = "done";
        tutorial.chapters = tutorial.chapters.map((chapter) => chapter.map(() => true));
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

    async onSwitchTutorials() {
        await this.orm.write("res.users", [user.userId], {
            tutorial_enabled: !this.tutorialsEnabled,
        });
        location.reload();
    }

    /**
     * Always shows the tips of the tutorials, or only while hovering them,
     * right away
     */
    async onSwitchTips() {
        const tipsShown = !this.state.tipsShown;
        await this.orm.write("res.users", [user.userId], { tutorial_tips_shown: tipsShown });
        this.state.tipsShown = session.tutorial_tips_shown = pointerState.tipsShown = tipsShown;
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
