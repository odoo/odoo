import { Mutex } from "@web/core/utils/concurrency";
import { TutorialChapter } from "@web_tutorial/tutorial/tutorial_chapter";

/**
 * @param {TutorialStepDefinition[]} steps
 * @returns {TutorialStepDefinition[][]} the steps by chapter: the successive
 *   steps of the same model and view types, the ones without action joining
 *   the action of the chapter (e.g. New of the starting action, then the
 *   fields of its quick create)
 */
function groupByChapter(steps) {
    const chapters = [];
    for (const step of steps) {
        const chapter = chapters.at(-1);
        const [first] = chapter || [];
        const actionId = chapter?.find(({ action_id }) => action_id)?.action_id;
        if (
            first?.res_model === step.res_model &&
            first.view_types.join() === step.view_types.join() &&
            (!step.action_id || step.action_id === actionId)
        ) {
            chapter.push(step);
        } else {
            chapters.push([step]);
        }
    }
    return chapters;
}

/**
 * A tutorial running for the user, going on from its last started chapter,
 * saving their progress
 */
export class Tutorial {
    /**
     * The saves of its progress, each one waiting for the previous one: the
     * server applies them in the order of the steps
     */
    #savingMutex = new Mutex();

    /**
     * @param {Object} data the tutorial as returned by the server, with its
     *   steps (see `web_tutorial.tutorial._get_tutorial_data`)
     * @param {import("@web/core/orm_plugin").ORM} orm
     */
    constructor(data, orm) {
        this.orm = orm;
        /** Whether the user opened its tooltips (from a link) */
        this.userExpandsMessages = data.user_expand_messages;
        /** Whether the tooltip of its steps is shown without hovering */
        this.expandMessages = data.expand_messages || this.userExpandsMessages;
        this.id = data.id;
        this.endMessage = data.end_message;
        const doneStepIds = new Set(data.done_steps);
        /** @type {TutorialChapter[]} */
        this.chapters = groupByChapter(data.steps).map(
            (stepDefinitions, index) =>
                new TutorialChapter(stepDefinitions, doneStepIds, this, index)
        );
        /** The index of the current chapter */
        this.chapterIndex = Math.max(
            this.chapters.findLastIndex((chapter) => chapter.steps.some((step) => step.done)),
            0
        );
        /** @type {TutorialStep[]} the steps of all its chapters, in order */
        this.steps = this.chapters.flatMap((chapter) => chapter.steps);
    }

    /** Ends it for the user: finished or skipped */
    end() {
        this.#save("mark_done", [[this.id]]);
    }

    /**
     * @param {ParentNode} root the document, or the dialog on top of the others
     * @param {DisplayedView} [view] the view displayed in the root
     * @returns {TutorialStep[]} the steps of the chapter shown in the root:
     *   the current chapter (or the one right after it, once done and shown
     *   too, e.g. after a chapter of all views), after the fields left to
     *   fill in of the kanban chapters of its model right before it (e.g. its
     *   form opened without the quick create of its kanban view); otherwise
     *   the last previous chapter to go back to
     */
    getDisplayedSteps(root, view) {
        const shownChapters = this.chapters.filter((chapter) => chapter.isShownIn(root, view));
        const chaptersToGoOn = shownChapters.filter((chapter) => chapter.index >= this.chapterIndex);
        let chapterToGoOn = chaptersToGoOn[0];
        for (const next of chaptersToGoOn.slice(1)) {
            if (!chapterToGoOn.isDone || next.index !== chapterToGoOn.index + 1) {
                break;
            }
            chapterToGoOn = next;
        }
        if (chapterToGoOn) {
            return [...this.#getSkippedFields(chapterToGoOn), ...chapterToGoOn.getStepsToGoOn()];
        }
        return shownChapters.at(-1)?.getStepsToGoBack() || [];
    }

    /**
     * Marks its step as done and saves it, a done step being done again
     * resetting the done steps after it; once finished, it's saved as such
     * by `end`, not to write its progress twice at once
     * @param {TutorialStep} step
     */
    markStepDone(step) {
        if (step.done) {
            const undone = this.#resetStepsAfter(step);
            if (undone.length) {
                this.#save("mark_steps_undone", [[this.id], undone.map(({ id }) => id)]);
            }
            return;
        }
        step.done = true;
        this.chapterIndex = Math.max(this.chapterIndex, step.chapter.index);
        if (!this.isDone) {
            this.#save("mark_steps_done", [[this.id], [step.id]]);
        }
    }

    /** Whether the steps of its last chapter are done */
    get isDone() {
        return this.chapters.at(-1).isDone;
    }

    /**
     * @param {TutorialChapter} formChapter
     * @returns {TutorialStep[]} the field steps not done of the chapters of
     *   the kanban views (not of the forms) of its model right before the form
     *   chapter, the fields of their quick create being the ones of the form too
     */
    #getSkippedFields(formChapter) {
        const steps = [];
        if (!formChapter.viewTypes.includes("form")) {
            return steps;
        }
        for (let index = formChapter.index - 1; index >= 0; index--) {
            const chapter = this.chapters[index];
            if (
                !chapter.viewTypes.includes("kanban") ||
                chapter.viewTypes.includes("form") ||
                chapter.resModel !== formChapter.resModel
            ) {
                break;
            }
            steps.unshift(...chapter.steps.filter((step) => step.type === "field" && !step.done));
        }
        return steps;
    }

    /**
     * Resets the done steps after the step, done again, going on from its
     * chapter
     * @param {TutorialStep} step
     * @returns {TutorialStep[]} the steps reset
     */
    #resetStepsAfter(step) {
        const index = this.steps.indexOf(step);
        const nextSteps = this.steps.slice(index + 1).filter((nextStep) => nextStep.done);
        for (const nextStep of nextSteps) {
            nextStep.done = false;
        }
        this.chapterIndex = step.chapter.index;
        return nextSteps;
    }

    /**
     * Saves its progress once the previous save is done; a failed save (e.g.
     * offline) is ignored, not to interrupt the user
     * @param {string} method
     * @param {any[]} args
     */
    #save(method, args) {
        this.#savingMutex
            .exec(() => this.orm.silent.call("web_tutorial.tutorial", method, args))
            .catch(() => {});
    }
}
