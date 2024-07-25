/** @odoo-module **/

import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { Tour } from "./tour";
import { TourStepAutomatic } from "./tour_step_automatic";

export class TourAutomatic extends Tour {
    mode = "auto";
    constructor(data, macroEngine) {
        super(data);
        this.buildSteps();
        this.steps = this.steps.map((step) => new TourStepAutomatic(step));
        this.macroEngine = macroEngine;
        return this;
    }

    start(pointer, callback) {
        // IMPROVEMENTS: Custom step compiler. Will probably require decoupling from `mode`.
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
        return this;
    }
}
