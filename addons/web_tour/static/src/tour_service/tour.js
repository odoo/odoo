import { validate } from "@odoo/owl";
import { StepSchema, TourStep } from "./tour_step";
import { tourState } from "./tour_state";
import { pick } from "@web/core/utils/objects";

const TourSchema = {
    name: { type: String },
    steps: { type: Array, element: StepSchema },
    url: { type: String, optional: true },
    rainbowManMessage: { type: [String, Function], optional: true },
    rainbowMan: { type: Boolean, optional: true },
    sequence: { type: Number, optional: true },
    checkDelay: { type: Number, optional: true },
    test: { type: Boolean, optional: true },
    saveAs: { type: String, optional: true },
    fadeout: { type: String, optional: true },
    wait_for: { type: [Function, Object], optional: true },
};

/**
 * @typedef Tour
 * @property {string} url
 * @property {string} name
 * @property {() => TourStep[]} steps
 * @property {boolean} [rainbowMan]
 * @property {number} [sequence]
 * @property {boolean} [test]
 * @property {Promise<any>} [wait_for]
 * @property {string} [saveAs]
 * @property {string} [fadeout]
 * @property {number} [checkDelay]
 */
export class Tour {
    mode = null;
    steps = [];
    schemaValidated = false;
    constructor(data) {
        data.test = !!data.test;
        this.validateSchema(data);
        this.wait_for = this.wait_for || Promise.resolve();
        this.rainbowMan = this.rainbowMan === undefined ? true : !!this.rainbowMan;
        this.fadeout = this.fadeout || "medium";
        this.sequence = this.sequence || 1000;
        this.stepDelay = tourState.get(this.name, "stepDelay");
        this.showPointerDuration = tourState.get(this.name, "showPointerDuration");
        return this;
    }

    buildSteps() {
        if (!this.mode) {
            throw new Error(`Tour must have a mode ("auto"|"manual") to use buildedSteps`);
        }
        this.steps = this.steps.map((step, index) => {
            const tourStep = new TourStep(step, this);
            tourStep.index = index;
            return tourStep;
        });
    }

    validateSchema(data) {
        try {
            if (!data.schemaValidated && !this.schemaValidated) {
                validate(data, TourSchema);
            }
            const allowedKeys = [...Object.keys(TourSchema)];
            Object.assign(this, pick(data, ...allowedKeys));
        } catch (error) {
            console.error(
                `Error in schema for Tour ${JSON.stringify(data, null, 4)}\n${error.message}`
            );
        }
        this.schemaValidated = true;
    }
}
