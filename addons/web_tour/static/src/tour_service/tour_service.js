/** @odoo-module **/

import { markup, whenReady, reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { MacroEngine } from "@web/core/macro";
import { registry } from "@web/core/registry";
import { config as transitionConfig } from "@web/core/transition";
import { session } from "@web/session";
import { TourPointer } from "../tour_pointer/tour_pointer";
import { TourPointerContainer } from "./tour_pointer_container";
import { compileStepAuto, compileStepManual, compileTourToMacro } from "./tour_compilers";
import { createPointerState } from "./tour_pointer_state";
import { tourState } from "./tour_state";
import { callWithUnloadCheck } from "./tour_utils";

/**
 * @typedef {string} JQuerySelector
 * @typedef {import("./tour_utils").RunCommand} RunCommand
 *
 * @typedef Tour
 * @property {string} url
 * @property {TourStep[]} steps
 * @property {boolean} [rainbowMan]
 * @property {number} [sequence]
 * @property {boolean} [test]
 * @property {Promise<any>} [wait_for]
 * @property {string} [saveAs]
 * @property {string} [fadeout]
 * @property {number} [checkDelay]
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
 * @property {boolean} [noPrepend]
 * @property {string} [consumeEvent]
 * @property {boolean} [mobile]
 * @property {string} [title]
 *
 * @typedef {"manual" | "auto"} TourMode
 */

/** @type {() => { [k: string]: Tour }} */
function extractRegisteredTours() {
    const tours = {};
    for (const [name, tour] of registry.category("web_tour.tours").getEntries()) {
        tours[name] = {
            name: tour.saveAs || name,
            steps: tour.steps,
            url: tour.url,
            rainbowMan: tour.rainbowMan === undefined ? true : !!tour.rainbowMan,
            rainbowManMessage: tour.rainbowManMessage,
            fadeout: tour.fadeout || "medium",
            sequence: tour.sequence || 1000,
            test: tour.test,
            wait_for: tour.wait_for || Promise.resolve(),
            checkDelay: tour.checkDelay,
        };
    }
    return tours;
}

export const tourService = {
    dependencies: ["orm", "effect", "ui"],
    start: async (_env, { orm, effect, ui }) => {
        await whenReady();

        const tours = extractRegisteredTours();
        const macroEngine = new MacroEngine({ target: document });
        const consumedTours = new Set(session.web_tours);

        const pointers = reactive({});

        registry.category("main_components").add("TourPointerContainer", {
            Component: TourPointerContainer,
            props: { pointers },
        });

        function createPointer(tourName, config) {
            const { state: pointerState, methods } = createPointerState();
            return {
                start() {
                    pointers[tourName] = {
                        id: tourName,
                        component: TourPointer,
                        props: { pointerState, ...config },
                    };
                },
                stop() {
                    delete pointers[tourName];
                    methods.destroy();
                },
                ...methods,
                pointTo(anchor, step) {
                    // `first` = first visible pointer.
                    const [first] = Object.values(pointers).filter(
                        (p) => p.props.pointerState.isVisible
                    );
                    if (!first || (first && first.id === tourName)) {
                        methods.pointTo(anchor, step);
                    }
                },
            };
        }

        /**
         * @param {TourStep} step
         * @param {TourMode} mode
         */
        function shouldOmit(step, mode) {
            const isDefined = (key, obj) => key in obj && obj[key] !== undefined;
            const getEdition = () =>
                session.server_version_info.slice(-1)[0] === "e" ? "enterprise" : "community";
            const correctEdition = isDefined("edition", step) ? step.edition === getEdition() : true;
            const correctDevice = isDefined("mobile", step) ? step.mobile === ui.isSmall : true;
            return (
                !correctEdition ||
                !correctDevice ||
                // `step.auto = true` means omitting a step in a manual tour.
                (mode === "manual" && step.auto)
            );
        }

        /**
         * @param {Tour} tour
         * @param {ReturnType<typeof createPointer>} pointer
         * @param {Object} options
         * @param {TourMode} options.mode
         * @param {number} options.stepDelay
         * @param {boolean} options.keepWatchBrowser - do not close watch browser when the tour failed
         * @param {number} options.showPointerDuration
         * - Useful when watching auto tour.
         * - Show the pointer for some duration before performing calling the run method.
         */
        function convertToMacro(
            tour,
            pointer,
            { mode, stepDelay, keepWatchBrowser, showPointerDuration }
        ) {
            // IMPROVEMENTS: Custom step compiler. Will probably require decoupling from `mode`.
            const stepCompiler = mode === "auto" ? compileStepAuto : compileStepManual;
            const checkDelay = mode === "auto" ? tour.checkDelay : 100;
            const filteredSteps = tour.steps.filter((step) => !shouldOmit(step, mode));
            return compileTourToMacro(tour, {
                filteredSteps,
                stepCompiler,
                pointer,
                stepDelay,
                keepWatchBrowser,
                showPointerDuration,
                checkDelay,
                onTourEnd({ name, rainbowManMessage, fadeout }) {
                    if (mode === "auto") {
                        transitionConfig.disabled = false;
                    }
                    let message;
                    if (typeof rainbowManMessage === "function") {
                        message = rainbowManMessage({
                            isTourConsumed: (name) => consumedTours.has(name),
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
                        consumedTours.add(name);
                        orm.call("web_tour.tour", "consume", [[name]]);
                    }
                    pointer.stop();
                    // Used to signal the python test runner that the tour finished without error.
                    browser.console.log("test successful");
                },
            });
        }

        /**
         * Disable transition before starting an "auto" tour.
         * @param {Macro} macro
         * @param {'auto' | 'manual'} mode
         */
        function activateMacro(macro, mode) {
            if (mode === "auto") {
                transitionConfig.disabled = true;
            }
            macroEngine.activate(macro);
        }

        function startTour(tourName, options = {}) {
            const defaultOptions = {
                stepDelay: 0,
                keepWatchBrowser: false,
                mode: "auto",
                startUrl: "",
                showPointerDuration: 0,
            };
            options = Object.assign(defaultOptions, options);
            const tour = tours[tourName];
            if (!tour) {
                throw new Error(`Tour '${tourName}' is not found.`);
            }
            tourState.set(tourName, "currentIndex", 0);
            tourState.set(tourName, "stepDelay", options.stepDelay);
            tourState.set(tourName, "keepWatchBrowser", options.keepWatchBrowser);
            tourState.set(tourName, "showPointerDuration", options.showPointerDuration);
            tourState.set(tourName, "mode", options.mode);
            tourState.set(tourName, "sequence", tour.sequence);
            const pointer = createPointer(tourName, {
                bounce: !(options.mode === "auto" && options.keepWatchBrowser),
            });
            const macro = convertToMacro(tour, pointer, options);
            const willUnload = callWithUnloadCheck(() => {
                if (tour.url && tour.url !== options.startUrl) {
                    window.location.href = window.location.origin + tour.url;
                }
            });
            if (!willUnload) {
                pointer.start();
                activateMacro(macro, options.mode);
            }
        }

        function resumeTour(tourName) {
            const tour = tours[tourName];
            const stepDelay = tourState.get(tourName, "stepDelay");
            const keepWatchBrowser = tourState.get(tourName, "keepWatchBrowser");
            const showPointerDuration = tourState.get(tourName, "showPointerDuration");
            const mode = tourState.get(tourName, "mode");
            const pointer = createPointer(tourName, {
                bounce: !(mode === "auto" && keepWatchBrowser),
            });
            const macro = convertToMacro(tour, pointer, {
                mode,
                stepDelay,
                keepWatchBrowser,
                showPointerDuration,
            });
            pointer.start();
            activateMacro(macro, mode);
        }

        if (!window.frameElement) {
            // Resume running tours.
            for (const tourName of tourState.getActiveTourNames()) {
                if (tourName in tours) {
                    resumeTour(tourName);
                } else {
                    // If a tour found in the local storage is not found in the `tours` map,
                    // then it is an outdated tour state. It should be cleared.
                    tourState.clear(tourName);
                }
            }
        }

        odoo.startTour = startTour;
        odoo.isTourReady = (tourName) => tours[tourName].wait_for.then(() => true);

        return {
            startTour,
            getSortedTours() {
                return Object.values(tours).sort((t1, t2) => {
                    return t1.sequence - t2.sequence || (t1.name < t2.name ? -1 : 1);
                });
            },
        };
    },
};

registry.category("services").add("tour_service", tourService);
