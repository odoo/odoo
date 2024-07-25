import { validate } from "@odoo/owl";
import { session } from "@web/session";
import { utils } from "@web/core/ui/ui_service";
import * as hoot from "@odoo/hoot-dom";
import { pick } from "@web/core/utils/objects";

export const StepSchema = {
    id: { type: String, optional: true },
    trigger: { type: String },
    isActive: { type: Array, element: String, optional: true },
    content: { type: [String, Object], optional: true }, //allow object for _t && markup
    position: { type: String, optional: true },
    run: { type: [String, Function], optional: true },
    timeout: { type: Number, optional: true },
    title: { type: String, optional: true },
    debugHelp: { type: String, optional: true },
    noPrepend: { type: Boolean, optional: true },
    pause: { type: Boolean, optional: true }, //ONLY IN DEBUG MODE
    break: { type: Boolean, optional: true }, //ONLY IN DEBUG MODE
};

/**
 * @typedef TourStep
 * @property {"enterprise"|"community"|"mobile"|"desktop"|HootSelector[][]} isActive Active the step following {@link isActiveStep} filter
 * @property {string} [id]
 * @property {HootSelector} trigger The node on which the action will be executed.
 * @property {string} [content] Description of the step.
 * @property {"top" | "botton" | "left" | "right"} [position] The position where the UI helper is shown.
 * @property {RunCommand} [run] The action to perform when trigger conditions are verified.
 * @property {number} [timeout] By default, when the trigger node isn't found after 10000 milliseconds, it throws an error.
 * You can change this value to lengthen or shorten the time before the error occurs [ms].
 * @property {string} [title]
 */
export class TourStep {
    element = null;
    schemaValidated = false;
    constructor(data, tour) {
        this.validateSchema(data);
        this.tour = tour;
        if (!this.tour) {
            throw new Error(`TourStep instance must have a tour !`);
        }
        if (!this.tour.mode) {
            throw new Error(`Tour must have a mode "manual"|"auto"`);
        }
        return this;
    }

    /**
     * Check if a step is active dependant on step.isActive property
     * Note that when step.isActive is not defined, the step is active by default.
     * When a step is not active, it's just skipped and the tour continues to the next step.
     */
    get active() {
        const mode = this.tour.mode;
        const isSmall = utils.isSmall();
        const standardKeyWords = ["enterprise", "community", "mobile", "desktop", "auto", "manual"];
        const isActiveArray = Array.isArray(this.isActive) ? this.isActive : [];
        if (isActiveArray.length === 0) {
            return true;
        }
        const selectors = isActiveArray.filter((key) => !standardKeyWords.includes(key));
        if (selectors.length) {
            // if one of selectors is not found, step is skipped
            for (const selector of selectors) {
                const el = hoot.queryFirst(selector);
                if (!el) {
                    return false;
                }
            }
        }
        const checkMode =
            isActiveArray.includes(mode) ||
            (!isActiveArray.includes("manual") && !isActiveArray.includes("auto"));
        const edition =
            (session.server_version_info || "").at(-1) === "e" ? "enterprise" : "community";
        const checkEdition =
            isActiveArray.includes(edition) ||
            (!isActiveArray.includes("enterprise") && !isActiveArray.includes("community"));
        const onlyForMobile = isActiveArray.includes("mobile") && isSmall;
        const onlyForDesktop = isActiveArray.includes("desktop") && !isSmall;
        const checkDevice =
            onlyForMobile ||
            onlyForDesktop ||
            (!isActiveArray.includes("mobile") && !isActiveArray.includes("desktop"));
        return checkEdition && checkDevice && checkMode;
    }

    get describeMe() {
        return (
            `[${this.index + 1}/${this.tour.steps.length}] Tour ${this.tour.name} → Step ` +
            (this.content ? `${this.content} (trigger: ${this.trigger})` : this.trigger)
        );
    }

    validateSchema(data) {
        try {
            if (!data.schemaValidated && !this.schemaValidated) {
                validate(data, StepSchema);
            }
            const allowedKeys = [...Object.keys(StepSchema), "index"];
            Object.assign(this, pick(data, ...allowedKeys));
        } catch (error) {
            console.error(
                `Error in schema for TourStep ${JSON.stringify(data, null, 4)}\n${error.message}`
            );
        }
        this.schemaValidated = true;
    }
}
