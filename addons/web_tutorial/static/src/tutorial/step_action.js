import {
    animationFrame,
    drag,
    hover,
    queryAll,
    queryFirst,
    queryRect,
    waitUntil,
} from "@odoo/hoot-dom";
import { TutorialStep } from "@web_tutorial/tutorial/step";

/**
 * An action on the element of its trigger, done once the user did it:
 * - `click`: once clicked (focused, for an input); Next goes on with the
 *   first item of the dropdown it opens (e.g. "New Project" in a New button
 *   proposing templates), unless the next step is in its menu (e.g. Delete
 *   in the actions menu);
 * - `drag`: once the user starts to drag it, the next step dropping it;
 * - `drop`: once the element of the previous step is dropped onto it.
 */
export class TutorialStepAction extends TutorialStep {
    /**
     * @param {TutorialStepDefinition} definition
     * @param {string} key
     * @param {boolean} done
     * @param {TutorialChapter} chapter
     */
    constructor(definition, key, done, chapter) {
        super(definition, key, done, chapter);
        /** @type {"click"|"drag"|"drop"} */
        this.action = definition.action;
        this.selector = definition.trigger;
    }

    /**
     * @param {ParentNode} root
     * @param {Element} target
     * @returns {boolean} whether the click on the target does the step: on its
     *   element, in the root or in a dropdown menu (rendered outside the root)
     */
    isDoneBy(root, target) {
        const el = this.action === "click" && this._closest(target);
        return Boolean(el && (root.contains(el) || el.closest(".o-dropdown--menu")));
    }

    /**
     * @param {Element} source
     * @returns {boolean} whether the user started to drag its element
     * @override
     */
    isDoneByDrag(source) {
        return this.action === "drag" && Boolean(this._closest(source));
    }

    /**
     * @param {ParentNode} root
     * @param {Element} source
     * @param {PointerEvent} ev
     * @returns {boolean} whether the element of the previous step was dropped
     *   onto its element
     * @override
     */
    isDoneByDrop(root, source, ev) {
        if (this.action !== "drop" || !this._getDragStep().isDoneByDrag(source)) {
            return false;
        }
        const el = this.findAnchor(root);
        if (!el) {
            return false;
        }
        const { bottom, left, right, top } = queryRect(el);
        return (
            ev.clientX >= left && ev.clientX <= right && ev.clientY >= top && ev.clientY <= bottom
        );
    }

    /**
     * Clicks the anchor (and the first item of the dropdown it opens, unless
     * the next step is in its menu), or drags it onto the element of the next
     * step, moving it a bit first for the drag to start; a drop is done with
     * its drag
     * @override
     */
    async _act(anchor, root) {
        if (this.action === "drag") {
            const { drop, moveTo } = await drag(anchor);
            await hover(anchor, { position: { left: 20, top: 20 }, relative: true });
            await animationFrame();
            await moveTo(this._getNextStep().findAnchor(root));
            await animationFrame();
            await drop();
        } else if (this.action === "click") {
            anchor.click();
            if (anchor.matches(".o-dropdown")) {
                await waitUntil(() => anchor.ariaExpanded === "true");
                if (!this._getNextStep()?.findAnchor(document)) {
                    queryFirst(".o-dropdown--menu .o-dropdown-item", { visible: true })?.click();
                }
            }
        }
    }

    /**
     * @param {Element} target
     * @returns {HTMLElement | undefined} the element of its trigger containing
     *   the target, its selector possibly using the pseudo-classes of hoot-dom
     *   (e.g. `:contains`)
     * @private
     */
    _closest(target) {
        return queryAll(this.selector).find((el) => el.contains(target));
    }

    /**
     * @returns {TutorialStepAction} the step dragging the element it drops
     * @private
     */
    _getDragStep() {
        return this.chapter.steps[this.chapter.steps.indexOf(this) - 1];
    }

    /**
     * @returns {TutorialStep | undefined} the next step of its chapter, e.g.
     *   the one dropping the element it drags
     * @private
     */
    _getNextStep() {
        return this.chapter.steps[this.chapter.steps.indexOf(this) + 1];
    }
}
