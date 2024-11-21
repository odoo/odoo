import { session } from "@web/session";
import { utils } from "@web/core/ui/ui_service";
import * as hoot from "@odoo/hoot-dom";
import { pick } from "@web/core/utils/objects";

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
 */
export class TourStep {
    constructor(data, tour) {
        Object.assign(this, data);
        this.tour = tour;
    }

    /**
     * Check if a step is active dependant on step.isActive property
     * Note that when step.isActive is not defined, the step is active by default.
     * When a step is not active, it's just skipped and the tour continues to the next step.
     */
    get active() {
        this.checkHasTour();
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

    checkHasTour() {
        if (!this.tour) {
            throw new Error(`TourStep instance must have a tour`);
        }
    }

    get describeMe() {
        this.checkHasTour();
        return (
            `[${this.index + 1}/${this.tour.steps.length}] Tour ${this.tour.name} → Step ` +
            (this.content ? `${this.content} (trigger: ${this.trigger})` : this.trigger)
        );
    }

    get stringify() {
        return (
            JSON.stringify(
                pick(this, "isActive", "content", "trigger", "run", "tooltipPosition", "timeout"),
                (_key, value) => {
                    if (typeof value === "function") {
                        return "[function]";
                    } else {
                        return value;
                    }
                },
                2
            ) + ","
        );
    }
}
