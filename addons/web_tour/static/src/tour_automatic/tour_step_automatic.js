import * as hoot from "@odoo/hoot-dom";
import { tourState } from "@web_tour/tour_state";
import { TourStep } from "@web_tour/tour_step";

export class TourStepAutomatic extends TourStep {
    constructor(data, tour, index) {
        super(data, tour);
        this.index = index;
    }

    /**
     * Splits this step into the pair of {@link Macro} step descriptors
     * {@link TourAutomatic} plays it with: one to log/pause for debugging,
     * one to actually wait for the trigger and perform the action.
     * @returns {{action: Function}[]}
     */
    get actions() {
        return [
            {
                action: async () => {
                    if (this.tour.debugMode) {
                        console.groupCollapsed(this.describeMe);
                        console.log(this.stringify);
                        if (this.tour.config.stepDelay > 0) {
                            await hoot.delay(this.tour.config.stepDelay);
                        }
                        if (this.break) {
                            // eslint-disable-next-line no-debugger
                            debugger;
                        }
                    } else {
                        console.log(this.describeMe);
                    }
                },
            },
            {
                trigger: this.trigger ? () => this.findTrigger() : null,
                timeout:
                    this.pause && this.tour.debugMode
                        ? 9999999
                        : this.timeout || this.tour.timeout || 10000,
                action: async (trigger) => {
                    this.tour.allowUnload = false;
                    if (!this.skipped && this.expectUnloadPage) {
                        this.tour.allowUnload = true;
                        setTimeout(() => {
                            const message = `
                                The key { expectUnloadPage } is defined but page has not been unloaded within 20000 ms.
                                You probably don't need it.
                            `.replace(/^\s+/gm, "");
                            this.tour.throwError(message);
                        }, 20000);
                    }
                    await this.doAction(this.element);
                    if (this.tour.debugMode) {
                        console.log(trigger);
                        if (this.skipped) {
                            console.log("This step has been skipped");
                        } else {
                            console.log("This step has run successfully");
                        }
                        console.groupEnd();
                        if (this.pause) {
                            await this.tour.pause();
                        }
                    }
                    tourState.setCurrentIndex(this.index + 1);
                    if (this.tour.allowUnload) {
                        return "StopTheMacro!";
                    }
                },
            },
        ];
    }
}
