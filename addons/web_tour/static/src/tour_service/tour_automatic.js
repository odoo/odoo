import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "./tour_step_automatic";
import { MacroEngine } from "@web/core/macro";

export class TourAutomatic {
    mode = "auto";
    pointer = null;
    constructor(data) {
        Object.assign(this, data);
        this.steps = this.steps.map((step, index) => new TourStepAutomatic(step, this, index));
        this.macroEngine = new MacroEngine({
            target: document,
            defaultCheckDelay: 500,
        });
        const tourConfig = tourState.getCurrentConfig();
        this.stepDelay = tourConfig.stepDelay;
    }

    get debugMode() {
        const tourConfig = tourState.getCurrentConfig() || {};
        return tourConfig.debug !== false;
    }

    start(pointer, callback) {
        this.pointer = pointer;
        const currentStepIndex = tourState.getCurrentIndex();
        const macroSteps = this.steps
            .filter((step) => step.index >= currentStepIndex)
            .flatMap((step) => {
                return [
                    {
                        action: () => step.log(),
                    },
                    {
                        trigger: () => step.findTrigger(),
                        action: (stepEl) => step.doAction(stepEl),
                    },
                    {
                        action: () => step.waitForPause(),
                    },
                ];
            })
            .concat([
                {
                    action: () => {
                        if (tourState.getCurrentTourOnError()) {
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

        transitionConfig.disabled = true;
        //Activate macro in exclusive mode (only one macro per MacroEngine)
        this.macroEngine.activate(macro, true);
    }
}
