import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "./tour_step_automatic";

export class TourAutomatic {
    mode = "auto";
    constructor(data, macroEngine) {
        Object.assign(this, data);
        this.steps = this.steps.map((step, index) => new TourStepAutomatic(step, this, index));
        this.macroEngine = macroEngine;
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
            name: this.name,
            checkDelay: this.checkDelay,
            steps: macroSteps,
        };

        pointer.start();
        transitionConfig.disabled = true;
        this.macroEngine.activate(macro, true);
    }
}
