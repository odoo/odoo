import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { TourStepAutomatic } from "./tour_step_automatic";
import { MacroEngine } from "@web/core/macro";
import { browser } from "@web/core/browser/browser";

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

    get currentIndex() {
        return tourState.getCurrentIndex();
    }

    get currentStep() {
        return this.steps[this.currentIndex];
    }

    get debugMode() {
        const tourConfig = tourState.getCurrentConfig() || {};
        return tourConfig.debug !== false;
    }

    start(pointer, callback) {
        const macroSteps = this.steps
            .filter((step) => step.index >= this.currentIndex)
            .flatMap((step) => {
                return [
                    {
                        action: () => step.log(),
                    },
                    {
                        trigger: () => step.findTrigger(),
                        action: async () => {
                            tourState.setCurrentIndex(step.index + 1);
                            if (!step.skipped && this.showPointerDuration > 0 && step.element) {
                                // Useful in watch mode.
                                pointer.pointTo(step.element, this);
                                await new Promise((r) =>
                                    browser.setTimeout(r, this.showPointerDuration)
                                );
                                pointer.hide();
                            }
                            return step.doAction();
                        },
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
