import { TutorialChapter } from "@web_tuto/tutorial/chapter";
import { getStepKeys } from "@web_tuto/plugin";

/** A tutorial running for the user, going on from its last started chapter */
export class Tutorial {
    /**
     * @param {Object} data the tutorial as returned by the server (see
     *   `web_tuto.tutorial._get_tutorial_json`)
     * @param {TutorialChapterDefinition[]} definition its chapters, in the
     *   registry "web_tuto.tutorials"
     */
    constructor(data, definition) {
        this.id = data.id;
        this.rainbowManMessage = data.rainbow_man_message;
        /** Whether the user drags an element, a drop step being only pointed meanwhile */
        this.isDragging = false;
        /** The URL saved to resume the tutorial at */
        this.resumeUrl = null;
        const stepKeys = getStepKeys(definition);
        const doneStepKeys = new Set(data.done_steps);
        /** @type {TutorialChapter[]} */
        this.chapters = definition.map(
            (chapterDefinition, index) =>
                new TutorialChapter(chapterDefinition, stepKeys[index], doneStepKeys, this)
        );
        /** The index of the current chapter */
        this.chapterIndex = Math.max(
            this.chapters.findLastIndex((chapter) => chapter.isStarted),
            0
        );
    }

    /**
     * @param {ParentNode} root the document, or the dialog on top of the others
     * @param {DisplayedView} [view] the view displayed in the root
     * @returns {TutorialStep[]} the steps of the chapter shown in the root:
     *   the first one from the current chapter, otherwise the last previous
     *   one to go back to
     */
    getDisplayedSteps(root, view) {
        const shownChapters = this.chapters.filter((chapter) => chapter.isShownIn(root, view));
        const chapterToGoOn = shownChapters.find((chapter) => chapter.index >= this.chapterIndex);
        if (chapterToGoOn) {
            return chapterToGoOn.getStepsToGoOn();
        }
        return shownChapters.at(-1)?.getStepsToGoBack() || [];
    }

    /** Whether the steps of its last chapter are done */
    get isDone() {
        return this.chapters.at(-1).isDone;
    }

    /** @returns {TutorialStep[]} the steps of all its chapters, in order */
    get steps() {
        return this.chapters.flatMap((chapter) => chapter.steps);
    }
}
