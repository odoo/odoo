import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "./tour_step_automatic";
import { validate } from "@odoo/owl";

const engineSchema = {
    steps: {
        type: Array,
        element: {
            trigger: { type: Function, optional: true },
            action: { type: Function },
        },
    },
};

class TourEngine {
    currentIndex = 0;
    isComplete = false;
    constructor(data) {
        validate(data, engineSchema);
        Object.assign(this, data);
        this.advance();
    }

    async advance() {
        if (this.isComplete) {
            return;
        }
        let el;
        const step = this.steps[this.currentIndex];
        let proceedToAction = !step.trigger;
        if (typeof step.trigger === "function") {
            el = await step.trigger();
            proceedToAction = !!el;
        }
        if (proceedToAction) {
            let actionResult;
            try {
                actionResult = await step.action(el);
            } catch (error) {
                throw new Error(error);
            }
            if (!actionResult) {
                this.currentIndex++;
                if (this.currentIndex === this.steps.length) {
                    this.isComplete = true;
                } else {
                    await this.advance();
                }
            }
        }
    }
}

export class TourAutomatic {
    mode = "auto";
    constructor(data) {
        Object.assign(this, data);
        this.steps = this.steps.map((step, index) => new TourStepAutomatic(step, this, index));
        this.stepDelay = +tourState.get(this.name, "stepDelay") || 0;
    }

    start(pointer, callback) {
        const currentStepIndex = tourState.get(this.name, "currentIndex");
        const macroSteps = this.steps
            .filter((step) => step.index >= currentStepIndex)
            .flatMap((step) => step.compileToMacro(pointer))
            .concat([
                {
                    action: () => {
                        if (tourState.get(this.name, "stepState") === "errored") {
                            console.error("tour not succeeded");
                        } else {
                            transitionConfig.disabled = false;
                            callback();
                        }
                    },
                },
            ]);

        const macro = {
            steps: macroSteps,
        };

        pointer.start();
        transitionConfig.disabled = true;
        new TourEngine(macro);
    }
}
