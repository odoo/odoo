/** @odoo-module **/

import { EventBus, markup, whenReady, reactive, validate } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { MacroEngine } from "@web/core/macro";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { TourPointer } from "../tour_pointer/tour_pointer";
import { createPointerState } from "./tour_pointer_state";
import { tourState } from "./tour_state";
import { callWithUnloadCheck } from "./tour_utils";
import { TourInteractive } from "./tour_interactive";
import { TourAutomatic } from "./tour_automatic";

const StepSchema = {
    id: { type: String, optional: true },
    content: { type: [String, Object], optional: true }, //allow object(_t && markup)
    debugHelp: { type: String, optional: true },
    isActive: { type: Array, element: String, optional: true },
    noPrepend: { type: Boolean, optional: true },
    run: { type: [String, Function], optional: true },
    timeout: { type: Number, optional: true },
    tooltipPosition: { type: String, optional: true },
    trigger: { type: String },
    //ONLY IN DEBUG MODE
    pause: { type: Boolean, optional: true },
    break: { type: Boolean, optional: true },
};

const TourSchema = {
    name: { type: String, optional: true },
    steps: Function,
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

registry.category("web_tour.tours").addValidation(TourSchema);

export const tourService = {
    // localization dependency to make sure translations used by tours are loaded
    dependencies: ["orm", "effect", "overlay", "localization"],
    start: async (_env, { orm, effect, overlay }) => {
        await whenReady();
        const toursEnabled = "tour_disable" in session && !session.tour_disable;
        const consumedTours = new Set(session.web_tours);

        /** @type {{ [k: string]: Tour }} */
        const tours = {};
        const tourRegistry = registry.category("web_tour.tours");
        function register(name, tour) {
            name = tour.saveAs || name;
            const wait_for = tour.wait_for || Promise.resolve();
            tours[name] = {
                wait_for,
                name,
                get steps() {
                    const steps = [];
                    for (const step of tour.steps()) {
                        try {
                            validate(step, StepSchema);
                        } catch (error) {
                            console.error(
                                `Error in schema for TourStep ${JSON.stringify(step, null, 4)}\n${
                                    error.message
                                }`
                            );
                        }
                        steps.push(step);
                    }
                    return steps;
                },
                url: tour.url,
                rainbowMan: tour.rainbowMan === undefined ? true : !!tour.rainbowMan,
                rainbowManMessage: tour.rainbowManMessage,
                fadeout: tour.fadeout || "medium",
                sequence: tour.sequence || 1000,
                test: tour.test,
                checkDelay: tour.checkDelay,
            };
            wait_for.then(() => {
                if (
                    !tour.test &&
                    toursEnabled &&
                    !consumedTours.has(name) &&
                    !tourState.getActiveTourNames().includes(name)
                ) {
                    startTour(name, { mode: "manual", redirect: false });
                }
            });
        }
        for (const [name, tour] of tourRegistry.getEntries()) {
            register(name, tour);
        }
        tourRegistry.addEventListener("UPDATE", ({ detail: { key, value } }) => {
            if (tourRegistry.contains(key)) {
                register(key, value);
                if (
                    tourState.getActiveTourNames().includes(key) &&
                    // Don't resume onboarding tours when tours are disabled
                    (toursEnabled || tourState.get(key, "mode") === "auto")
                ) {
                    resumeTour(key);
                }
            } else {
                delete tours[value];
            }
        });

        const bus = new EventBus();
        const macroEngine = new MacroEngine({ target: document });

        const pointers = reactive({});
        /** @type {Set<string>} */
        const runningTours = new Set();

        // FIXME: this is a hack for stable: whenever the macros advance, for each call to pointTo,
        // we push a function that will do the pointing as well as the tour name. Then after
        // a microtask tick, when all pointTo calls have been made by the macro system, we can sort
        // these by tour priority/sequence and only call the one with the highest priority so we
        // show the correct pointer.
        const possiblePointTos = [];
        function createPointer(tourName, config) {
            const { state: pointerState, methods } = createPointerState();
            let remove;
            return {
                start() {
                    pointers[tourName] = {
                        methods,
                        id: tourName,
                        component: TourPointer,
                        props: { pointerState, ...config },
                    };
                    remove = overlay.add(pointers[tourName].component, pointers[tourName].props, {
                        sequence: 1100, // sequence based on bootstrap z-index values.
                    });
                },
                stop() {
                    remove?.();
                    delete pointers[tourName];
                    methods.destroy();
                },
                ...methods,
                async pointTo(anchor, step, isZone) {
                    possiblePointTos.push([tourName, () => methods.pointTo(anchor, step, isZone)]);
                    await Promise.resolve();
                    // only done once per macro advance
                    if (!possiblePointTos.length) {
                        return;
                    }
                    const toursByPriority = Object.fromEntries(
                        getSortedTours().map((t, i) => [t.name, i])
                    );
                    const sortedPointTos = possiblePointTos
                        .slice(0)
                        .sort(([a], [b]) => toursByPriority[a] - toursByPriority[b]);
                    possiblePointTos.splice(0); // reset for the next macro advance

                    const active = sortedPointTos[0];
                    const [activeId, enablePointer] = active || [];
                    for (const { id, methods } of Object.values(pointers)) {
                        if (id === activeId) {
                            enablePointer();
                        } else {
                            methods.hide();
                        }
                    }
                },
            };
        }

        function showRainbowManMessage({ rainbowManMessage, fadeout }) {
            let message;
            if (typeof rainbowManMessage === "function") {
                message = rainbowManMessage({
                    isTourConsumed: (name) => consumedTours.has(name),
                });
            } else if (typeof rainbowManMessage === "string") {
                message = rainbowManMessage;
            } else {
                message = markup(
                    _t("<strong><b>Good job!</b> You went through all steps of this tour.</strong>")
                );
            }
            effect.add({ type: "rainbow_man", message, fadeout });
        }

        function endTour({ name }) {
            bus.trigger("TOUR-FINISHED");
            // Used to signal the python test runner that the tour finished without error.
            browser.console.log("tour succeeded");
            // Used to see easily in the python console and to know which tour has been succeeded in suite tours case.
            const succeeded = `║ TOUR ${name} SUCCEEDED ║`;
            const msg = [succeeded];
            msg.unshift("╔" + "═".repeat(succeeded.length - 2) + "╗");
            msg.push("╚" + "═".repeat(succeeded.length - 2) + "╝");
            browser.console.log(`\n\n${msg.join("\n")}\n`);
            consumedTours.add(name);
            runningTours.delete(name);
            tourState.clear(name);
        }

        function startTour(tourName, options = {}) {
            if (runningTours.has(tourName) && options.mode === "manual") {
                return;
            }
            runningTours.add(tourName);
            const defaultOptions = {
                stepDelay: 0,
                keepWatchBrowser: false,
                mode: "auto",
                startUrl: "",
                showPointerDuration: 0,
                redirect: true,
                debug: false,
            };
            options = Object.assign(defaultOptions, options);
            const tour = tours[tourName];
            if (!tour) {
                throw new Error(`Tour '${tourName}' is not found.`);
            }
            tourState.set(tourName, "currentIndex", 0);
            tourState.set(tourName, "stepDelay", options.stepDelay);
            tourState.set(tourName, "keepWatchBrowser", options.keepWatchBrowser);
            tourState.set(tourName, "debug", options.debug);
            tourState.set(tourName, "showPointerDuration", options.showPointerDuration);
            tourState.set(tourName, "mode", options.mode);
            tourState.set(tourName, "sequence", tour.sequence);
            if (tourState.get(tourName, "debug") !== false) {
                // Starts the tour with a debugger to allow you to choose devtools configuration.
                // eslint-disable-next-line no-debugger
                debugger;
            }
            const pointer = createPointer(tourName, {
                bounce: !(options.mode === "auto" && options.keepWatchBrowser),
            });

            const willUnload = callWithUnloadCheck(() => {
                if (tour.url && tour.url !== options.startUrl && options.redirect) {
                    browser.location.href = browser.location.origin + tour.url;
                }
            });

            if (!willUnload) {
                if (options.mode === "auto") {
                    new TourAutomatic(tour, macroEngine).start(pointer, () => {
                        pointer.stop();
                        endTour(tour);
                    });
                } else {
                    new TourInteractive(tour).start(pointer, () => {
                        pointer.stop();
                        orm.call("web_tour.tour", "consume", [[tour.name]]);
                        showRainbowManMessage(tour);
                        endTour(tour);
                    });
                }
            }
        }

        function resumeTour(tourName) {
            if (runningTours.has(tourName)) {
                return;
            }
            runningTours.add(tourName);
            const tour = tours[tourName];
            const keepWatchBrowser = tourState.get(tourName, "keepWatchBrowser");
            const mode = tourState.get(tourName, "mode");
            const pointer = createPointer(tourName, {
                bounce: !(mode === "auto" && keepWatchBrowser),
            });
            if (mode === "auto") {
                new TourAutomatic(tour, macroEngine).start(pointer, () => {
                    pointer.stop();
                    endTour(tour);
                });
            } else {
                new TourInteractive(tour).start(pointer, () => {
                    pointer.stop();
                    orm.call("web_tour.tour", "consume", [[tour.name]]);
                    showRainbowManMessage(tour);
                    endTour(tour);
                });
            }
        }

        function getSortedTours() {
            return Object.values(tours).sort((t1, t2) => {
                return t1.sequence - t2.sequence || (t1.name < t2.name ? -1 : 1);
            });
        }

        if (!window.frameElement) {
            const paramsTourName = new URLSearchParams(browser.location.search).get("tour");
            if (paramsTourName && paramsTourName in tours) {
                startTour(paramsTourName, { mode: "manual " });
            }
            // Resume running tours.
            for (const tourName of tourState.getActiveTourNames()) {
                if (tourName in tours) {
                    resumeTour(tourName);
                }
            }
        }

        odoo.startTour = startTour;
        odoo.isTourReady = (tourName) => tours[tourName].wait_for.then(() => true);

        return {
            bus,
            startTour,
            resumeTour,
            getSortedTours,
        };
    },
};

registry.category("services").add("tour_service", tourService);
