import { queryAll, queryFirst, waitUntil } from "@odoo/hoot-dom";
import { TutorialStep } from "@web_tutorial/tutorial/tutorial_step";

const MENU_TOGGLE = ".o_control_panel .o_cp_action_menus button[data-hotkey='u']";

/**
 * An item of the actions menu of the view, done once clicked: a generic one
 * (`type: "generic_button"`, e.g. Delete), or a server action bound to the
 * model (`type: "server_action"`). The pointer shows the toggle of the menu
 * until it's open.
 */
export class TutorialStepMenuItem extends TutorialStep {
    /** The icons of the generic buttons of the actions menu */
    static ICONS = {
        Archive: "archive",
        Delete: "delete",
        Duplicate: "content_copy",
        Unarchive: "unarchive",
    };

    /**
     * @param {TutorialStepDefinition} definition
     * @param {boolean} done
     * @param {TutorialChapter} chapter
     */
    constructor(definition, done, chapter) {
        super(definition, done, chapter);
        this.actionName = definition.action_name;
        this.icon = TutorialStepMenuItem.ICONS[definition.name];
    }

    /**
     * @param {ParentNode} root
     * @returns {HTMLElement | null} its item if the menu is open, the toggle
     *   of the menu otherwise
     * @override
     */
    findAnchor(root) {
        const toggle = queryFirst(MENU_TOGGLE, { root, visible: true });
        if (!toggle || toggle.matches(":disabled")) {
            return null;
        }
        if (toggle.ariaExpanded !== "true") {
            return toggle;
        }
        const items = queryAll(".o-dropdown--menu .o-dropdown-item", { visible: true });
        return items.find((item) => this.#isItem(item)) || null;
    }

    /**
     * @param {ParentNode} root
     * @param {Element} target
     * @returns {boolean} whether the click on the target does the step: its
     *   item of the open actions menu, not an item of another dropdown with the
     *   same icon (e.g. deleting a message of the chatter)
     */
    isDoneBy(root, target) {
        const item = target.closest(".o-dropdown--menu .o-dropdown-item");
        return Boolean(item && item === this.findAnchor(root));
    }

    /**
     * Opens the menu for the user (Next), and clicks its item
     * @param {ParentNode} root
     * @override
     */
    async perform(root) {
        if (this.skippable) {
            return;
        }
        const toggle = queryFirst(MENU_TOGGLE, { root, visible: true });
        if (toggle && toggle.ariaExpanded !== "true") {
            toggle.click();
            await waitUntil(() => toggle.ariaExpanded === "true");
            if (this.done || !toggle.isConnected) {
                return;
            }
        }
        super.perform(root);
    }

    /**
     * @param {Element} item
     * @returns {boolean} whether the item of the menu is the one of the step
     */
    #isItem(item) {
        return this.icon
            ? Boolean(queryFirst(`[data-icon='${this.icon}']`, { root: item }))
            : item.textContent.trim() === this.actionName;
    }
}
