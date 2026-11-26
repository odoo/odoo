import { queryFirst, waitUntil } from "@odoo/hoot-dom";
import { TutorialStep } from "@web_tutorial/tutorial/tutorial_step";

/**
 * The generic buttons of the web client, outside the actions menu: New of
 * the views of several records, and Edit of a kanban quick create
 */
const GENERIC_BUTTONS = {
    Edit: ".o_kanban_quick_create .o_kanban_edit",
    New: `.o_control_panel :is(${[
        ".o_list_button_add",
        ".o-kanban-button-new",
        ".o_map_button_add",
        ".o_gantt_button_add",
        ".o_grid_button_add",
        ".o-calendar-button-new",
    ].join(", ")})`,
};

/**
 * A button of the view, done once clicked: the one calling the method of the
 * step (`type: "method"`), or a generic button of the web client
 * (`type: "generic_button"`): New, or Edit opening the form of a kanban quick
 * create
 */
export class TutorialStepButton extends TutorialStep {
    /**
     * @param {TutorialStepDefinition} definition
     * @param {boolean} done
     * @param {TutorialChapter} chapter
     */
    constructor(definition, done, chapter) {
        super(definition, done, chapter);
        this.selector =
            this.type === "method"
                ? `[type='object'][name='${definition.name}']`
                : GENERIC_BUTTONS[definition.name];
    }

    /**
     * @param {ParentNode} root
     * @param {Element} target
     * @returns {boolean} whether the click on the target does the step
     */
    isDoneBy(root, target) {
        const el = target.closest(this.selector);
        return Boolean(el && root.contains(el));
    }

    /**
     * Clicks its button for the user (Next), and the first item of the
     * dropdown it may open (e.g. a New button proposing templates)
     * @param {ParentNode} root
     * @override
     */
    async perform(root) {
        const anchor = this.findAnchor(root);
        super.perform(root, anchor);
        if (!this.skippable && anchor?.matches(".o-dropdown")) {
            await waitUntil(() => anchor.ariaExpanded === "true");
            queryFirst(".o-dropdown--menu .o-dropdown-item", { visible: true })?.click();
        }
    }
}
