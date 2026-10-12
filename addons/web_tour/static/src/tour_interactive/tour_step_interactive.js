import * as hoot from "@odoo/hoot-dom";
import { TourStep } from "@web_tour/tour_step";
import { TourAction } from "@web_tour/tour_interactive/tour_action";
import { pointerState } from "@web_tour/tour_pointer/tour_pointer";

export class TourStepInteractive extends TourStep {
    /**
     * Splits this step's `run` into the individual sub-actions (e.g. `drag_and_drop`
     * → "drag" then "drop") that {@link TourInteractive} plays one real DOM event at
     * a time.
     * @returns {TourAction[]}
     */
    get actions() {
        const actions = [];
        const addAction = (event, anchor) => {
            actions.push(new TourAction({ step: this, event, anchor }));
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

            if (action === "drag_and_drop") {
                addAction("drag", this.trigger);
                action = "drop";
            }

            addAction(action, ["edit", "editor"].includes(action) ? this.trigger : anchor);
        }

        return actions;
    }

    /**
     * Performs this step's action automatically, the same way an automatic
     * tour would (through {@link TourHelpers}), instead of waiting for a real user
     * interaction. The tour pointer is still resolved and displayed exactly as it
     * would be for a human, so this exercises the actual anchor-finding logic used
     * by onboarding tours. Called once per step by {@link TourInteractive.playRobot}.
     */
    async doAction() {
        try {
            await hoot.waitFor(".o_tour_pointer", { timeout: this.timeout || 10000 });
        } catch {
            console.error(this.error.join("\n"));
            this.tour.robotStep = null;
            return;
        }
        if (this.tour.config.stepDelay > 0) {
            await hoot.delay(this.tour.config.stepDelay);
        }
        if (!pointerState.trigger?.isConnected) {
            this.tour.robotStep = null;
            this.tour.anchorEl = undefined;
            this.tour.updatePointer();
            return;
        }
        if (pointerState.trigger.disabled) {
            try {
                await hoot.waitUntil(() => !pointerState.trigger?.disabled, { timeout: 10000 });
            } catch {
                this.tour.robotStep = null;
                return;
            }
            if (this.tour.currentAction.step !== this || !pointerState.trigger?.isConnected) {
                return;
            }
        }
        await super.doAction(pointerState.trigger);
    }
}
