import { TourStep } from "@web_tour/js/tour_step";

export class TourStepInteractive extends TourStep {
    /**
     * Splits this step's `run` into the individual sub-actions (e.g. `drag_and_drop`
     * → "drag" then "drop") that {@link TourInteractive} plays one real DOM event at
     * a time.
     * @returns {{
     *  step: TourStepInteractive,
     *  event: string,
     *  anchor: string,
     *  content?: string,
     *  tooltipPosition?: string,
     *  findTrigger: () => HTMLElement,
     * }[]}
     */
    get actions() {
        const actions = [];
        const addAction = (event, anchor, pointerInfo = {}) => {
            actions.push({
                step: this,
                event,
                anchor,
                ...pointerInfo,
                findTrigger: () => this.findTrigger(anchor, event),
            });
        };

        if (!this.run || typeof this.run === "function") {
            addAction("warn", this.trigger);
            return actions;
        }

        for (const todo of this.run.split("&&")) {
            const m = String(todo)
                .trim()
                .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);

            let action = m.groups?.action;
            const anchor = m.groups?.arguments || this.trigger;
            const pointerInfo = {
                content: this.content || this.getStepContent(action, anchor),
                tooltipPosition: this.tooltipPosition,
            };

            if (action === "drag_and_drop") {
                addAction("drag", this.trigger, pointerInfo);
                action = "drop";
            }

            addAction(action, action === "edit" ? this.trigger : anchor, pointerInfo);
        }

        return actions;
    }

    getStepContent(action, anchor) {
        if (action === "click") {
            return `Click on element`;
        } else if (action === "edit") {
            return `Edit element`;
        } else if (action === "drag_and_drop") {
            return `Drag element`;
        } else if (action === "press") {
            return `Press ${anchor}`;
        }
        return ``;
    }

    /**
     * Resolves the trigger element for one of this step's actions: applies the
     * same rules as {@link TourStep.findTrigger} (modal/overlay stacking,
     * UI-blocked, enabled, parent frame readiness, ...), then maps it to the
     * actual element to listen on for that action's event.
     * @param {string} trigger
     * @param {string} event
     * @returns {HTMLElement}
     */
    findTrigger(trigger, event) {
        const el = super.findTrigger(trigger);
        if (!el || el === true) {
            return undefined;
        }

        if (event === "drag") {
            // jQuery-ui draggable triggers 'drag' events on the .ui-draggable element,
            // but the tip is attached to the .ui-draggable-handle element which may
            // be one of its children (or the element itself
            return el.closest(
                ".ui-draggable, .o_draggable, .o_we_draggable, .o-draggable, [draggable='true']"
            );
        }
        if (event === "input" && !["textarea", "input"].includes(el.tagName.toLowerCase())) {
            return el.closest("[contenteditable='true']");
        }
        if (event === "sort") {
            // when an element is dragged inside a sortable container (with classname
            // 'ui-sortable'), jQuery triggers the 'sort' event on the container
            return el.closest(".ui-sortable, .o_sortable");
        }
        return el;
    }
}
