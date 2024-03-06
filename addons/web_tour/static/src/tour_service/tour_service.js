/** @odoo-module **/

import { markup, whenReady } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { config as transitionConfig } from "@web/core/transition";
import { TourPointer } from "../tour_pointer/tour_pointer";
import { tourState } from "./tour_state";
import { runner, getSortedTours } from "./tour_runner";

/**
 * @typedef {string} JQuerySelector
 * @typedef {import("./tour_utils").RunCommand} RunCommand
 *
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
 * @property {string|undefined} [shadow_dom]
 *
 * @typedef TourStep
 * @property {string} [id]
 * @property {JQuerySelector} trigger
 * @property {JQuerySelector} [extra_trigger]
 * @property {JQuerySelector} [alt_trigger]
 * @property {JQuerySelector} [skip_trigger]
 * @property {string} [content]
 * @property {"top" | "botton" | "left" | "right"} [position]
 * @property {"community" | "enterprise"} [edition]
 * @property {RunCommand} [run]
 * @property {boolean} [auto]
 * @property {boolean} [in_modal]
 * @property {number} [width]
 * @property {number} [timeout]
 * @property {boolean} [consumeVisibleOnly]
 * @property {string} [consumeEvent]
 * @property {boolean} [mobile]
 * @property {string} [title]
 * @property {string|false|undefined} [shadow_dom]
 * @property {object} [state]
 *
 * @typedef {"manual" | "auto"} TourMode
 */

export const tourService = {
    // localization dependency to make sure translations used by tours are loaded
    dependencies: ["orm", "effect", "overlay", "localization"],
    start: async (_env, { orm, effect, overlay }) => {
        await whenReady();
        const tourRegistry = registry.category("web_tour.tours");
        for (const [name, tour] of tourRegistry.getEntries()) {
            runner.register(name, tour);
        }
        tourRegistry.addEventListener("UPDATE", ({ detail: { key, value } }) => {
            if (tourRegistry.contains(key)) {
                runner.register(key, value);
                if (
                    tourState.getActiveTourNames().includes(key) &&
                    // Don't resume onboarding tours when tours are disabled
                    (runner.toursEnabled || tourState.get(key, "mode") === "auto")
                ) {
                    runner.resumeTour(key);
                }
            } else {
                delete runner.tours[value];
            }
        });

        runner.bus.addEventListener("TOUR_END", ({ detail }) => {
            const { name, rainbowManMessage, fadeout, mode } = detail;
            if (mode === "auto") {
                transitionConfig.disabled = false;
            }
            let message;
            if (typeof rainbowManMessage === "function") {
                message = rainbowManMessage({
                    isTourConsumed: (name) => runner.consumedTours.has(name),
                });
            } else if (typeof rainbowManMessage === "string") {
                message = rainbowManMessage;
            } else {
                message = markup(
                    _t(
                        "<strong><b>Good job!</b> You went through all steps of this tour.</strong>"
                    )
                );
            }
            effect.add({ type: "rainbow_man", message, fadeout });
            if (mode === "manual") {
                orm.call("web_tour.tour", "consume", [[name]]);
            }
        });

        const overlaysRemove = {};
        runner.bus.addEventListener("POINTER_CHANGE", ({ detail }) => {
            const { operation, pointer } = detail;
            if (operation === "add") {
                overlaysRemove[pointer.id] = overlay.add(TourPointer, pointer.props);
            } else {
                overlaysRemove[pointer.id]()
                delete overlaysRemove[pointer.id]
            }
        });

        if (!window.frameElement) {
            // Resume running tours.
            for (const tourName of tourState.getActiveTourNames()) {
                if (tourName in runner.tours) {
                    runner.resumeTour(tourName);
                }
            }
        }

        const startTour = runner.startTour.bind(runner);
        odoo.startTour = startTour;
        odoo.isTourReady = (tourName) => runner.tours[tourName].wait_for.then(() => true);

        return {
            bus: runner.bus,
            startTour,
            getSortedTours,
        };
    },
};

registry.category("services").add("tour_service", tourService);
