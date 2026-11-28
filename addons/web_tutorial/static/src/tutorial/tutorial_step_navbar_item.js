import { queryFirst, waitUntil } from "@odoo/hoot-dom";
import { TutorialStep } from "@web_tutorial/tutorial/tutorial_step";

/**
 * A menu of the app, done once clicked in the navbar (`type: "menu_item"`).
 * The pointer shows the section of the navbar opening it until it's open.
 */
export class TutorialStepNavbarItem extends TutorialStep {
    /**
     * @param {TutorialStepDefinition} definition
     * @param {boolean} done
     * @param {TutorialChapter} chapter
     */
    constructor(definition, done, chapter) {
        super(definition, done, chapter);
        const { menu_section, name } = definition;
        this.selector = `:is(.o_menu_sections, .o-dropdown--menu) a[data-menu-xmlid='${name}']`;
        /** The selector of the toggle of the section opening the menu */
        this.toggleSelector = `.o_menu_sections button[data-menu-xmlid='${menu_section}']`;
    }

    /**
     * @param {ParentNode} root
     * @returns {HTMLElement | null} its menu, or the toggle of its section
     *   while closed; none in a dialog, hiding the navbar
     * @override
     */
    findAnchor(root) {
        if (root !== document) {
            return null;
        }
        return super.findAnchor(root) || queryFirst(this.toggleSelector, { visible: true });
    }

    /**
     * @param {ParentNode} root
     * @param {Element} target
     * @returns {boolean} whether the click on the target does the step
     */
    isDoneBy(root, target) {
        return root === document && Boolean(target.closest(this.selector));
    }

    /**
     * Opens the section for the user (Next), and clicks its menu
     * @param {ParentNode} root
     * @override
     */
    async perform(root) {
        const anchor = this.findAnchor(root);
        if (this.skippable || !anchor?.matches(this.toggleSelector)) {
            return super.perform(root);
        }
        anchor.click();
        await waitUntil(() => anchor.ariaExpanded === "true");
        if (!this.done && anchor.isConnected) {
            super.perform(root);
        }
    }
}
