/** @odoo-module **/

import { tourState } from "./tour_state";
import { config as transitionConfig } from "@web/core/transition";
import { Tour } from "./tour";
import { TourStepAutomatic } from "./tour_step_automatic";
import { tourDebuggerPlayer } from "@web_tour/tour_debugger/tour_debugger_player";
import * as hoot from "@odoo/hoot-dom";
import { TourDebugger } from "@web_tour/tour_debugger/tour_debugger";

export class TourAutomatic extends Tour {
    mode = "auto";
    constructor(data, macroEngine, overlay) {
        super(data);
        this.buildSteps();
        this.steps = this.steps.map((step) => new TourStepAutomatic(step));
        this.macroEngine = macroEngine;
        this.startDebugger(overlay);
        return this;
    }

    async startDebugger(overlay) {
        if (tourState.get(this.name, "debug") !== false) {
            window.hoot = hoot;
            overlay.add(TourDebugger, { tour: this }, { sequence: 1987 });
            await tourDebuggerPlayer.waitFor("REPLAY").then(() => {
                // eslint-disable-next-line no-debugger
                debugger;
            });
        }
    }

    start(pointer, callback) {
        // IMPROVEMENTS: Custom step compiler. Will probably require decoupling from `mode`.
        const currentStepIndex = tourState.get(this.name, "currentIndex");
        const macroSteps = this.steps
            .filter((step) => step.index >= currentStepIndex)
            .flatMap((step) => step.compileToMacro(pointer))
            .concat([
                {
                    action: async () => {
                        tourDebuggerPlayer.setStatus("FINISHED");
                        const debugMode = tourState.get(this.name, "debug");
                        if (tourState.get(this.name, "stepState") === "errored") {
                            console.error("tour not succeeded");
                        } else {
                            transitionConfig.disabled = false;
                        }
                        if (debugMode !== false) {
                            await tourDebuggerPlayer.waitFor("STOP");
                        }
                        callback();
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
