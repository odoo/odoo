import { TutorialChapter } from "@web_tuto/tutorial/chapter";

/**
 * A tutorial running for the user: its chapters, with the steps done in each
 * of them. The current chapter is the last one with a done step: the user
 * goes on from there.
 */
export class Tutorial {
    /**
     * @param {Object} data the tutorial as returned by the server (see
     *   `web_tuto.tutorial._get_tutorial_json`)
     */
    constructor(data) {
        this.id = data.id;
        this.rainbowManMessage = data.rainbowManMessage;
        /** @type {TutorialChapter[]} */
        this.chapters = data.chapters.map((chapterData) => new TutorialChapter(chapterData, this));
        /** The index of the current chapter */
        this.chapterIndex = Math.max(
            this.chapters.findLastIndex((chapter) => chapter.isStarted),
            0
        );
    }

    /** @returns {TutorialStep[]} the steps of all its chapters, in order */
    get steps() {
        return this.chapters.flatMap((chapter) => chapter.steps);
    }

    /** Whether the steps of its last chapter are done */
    get isDone() {
        return this.chapters.at(-1).isDone;
    }

    /**
     * @param {ParentNode} root the document, or the dialog on top of the others
     * @param {Object} [props] the props of the view displayed in the root
     * @returns {TutorialStep[]} the steps of the chapter shown in the root, in
     *   the order they're proposed in: the first shown chapter from the
     *   current one to go on with it, otherwise the last shown previous one to
     *   go back to it (see `TutorialChapter.getStepsToGoOn` and
     *   `TutorialChapter.getStepsToGoBack`)
     */
    getDisplayedSteps(root, props) {
        const shownChapters = this.chapters.filter((chapter) => chapter.isShownIn(root, props));
        const chapterToGoOn = shownChapters.find((chapter) => chapter.index >= this.chapterIndex);
        if (chapterToGoOn) {
            return chapterToGoOn.getStepsToGoOn();
        }
        return shownChapters.at(-1)?.getStepsToGoBack() || [];
    }
}
