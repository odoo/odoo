/** @odoo-module **/

import { EventBus, markup, whenReady, reactive } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { MacroEngine } from "@web/core/macro";
import { registry } from "@web/core/registry";
import { config as transitionConfig } from "@web/core/transition";
import { session } from "@web/session";
import { TourPointer } from "../tour_pointer/tour_pointer";
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
 * @property {boolean} [noPrepend]
 * @property {string} [consumeEvent]
 * @property {boolean} [mobile]
 * @property {string} [title]
 * @property {string|false|undefined} [shadow_dom]
 *
 * @typedef {"manual" | "auto"} TourMode
 */

export const tourService = {
    // localization dependency to make sure translations used by tours are loaded
    dependencies: ["orm", "effect", "ui", "overlay", "localization"],
    start: async (_env, { orm, effect, ui, overlay }) => {
        await whenReady();

        /** @type {{ [k: string]: Tour }} */
        const tours = {};
        const tourRegistry = registry.category("web_tour.tours");
        function register(name, tour) {
            name = tour.saveAs || name
            tours[name] = {
                name,
                get steps() {
                    if (typeof tour.steps === "function") {
                        return tour.steps().map((step) => {
                            step.shadow_dom = step.shadow_dom ?? tour.shadow_dom;
                            return step;
                        });
                    } else {
                        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
                    }
                },
                shadow_dom: tour.shadow_dom,
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
        for (const [name, tour] of tourRegistry.getEntries()) {
            register(name, tour);
        }
        tourRegistry.addEventListener("UPDATE", ({ detail: { key, value } }) => {
            if (tourRegistry.contains(key)) {
                register(key, value);
                if (tourState.getActiveTourNames().includes(key)) {
                    resumeTour(key);
                }
            } else {
                delete tours[value];
            }
        });

        const bus = new EventBus();
        const macroEngine = new MacroEngine({ target: document });
        const consumedTours = new Set(session.web_tours);

        const pointers = reactive({});
        /** @type {Set<string>} */
        const runningTours = new Set();

        function createPointer(tourName, config) {
            const { state: pointerState, methods } = createPointerState();
            let remove;
            return {
                start() {
                    pointers[tourName] = {
                        id: tourName,
                        component: TourPointer,
                        props: { pointerState, ...config },
                    };
                    remove = overlay.add(pointers[tourName].component, pointers[tourName].props);
                },
                stop() {
                    remove?.();
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
            const correctEdition = isDefined("edition", step)
                ? step.edition === getEdition()
                : true;
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
                onStepConsummed(tour, step) {
                    bus.trigger("STEP-CONSUMMED", { tour, step });
                },
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
                    runningTours.delete(name);
                },
            });
        }

        /**
         * Wait for the shadow hosts matching the given selectors to
         * appear in the DOM then, register the underlying shadow roots
         * to the macro engine observer in order to listen to the
         * changes in the shadow DOM.
         *
         * @param {Set<string>} shadowHostSelectors
         */
        function observeShadows(shadowHostSelectors) {
            const observer = new MutationObserver(() => {
                const shadowRoots = [];
                for (const selector of shadowHostSelectors) {
                    const shadowHost = document.querySelector(selector);
                    if (shadowHost) {
                        shadowRoots.push(shadowHost.shadowRoot);
                        shadowHostSelectors.delete(selector);
                    }
                }
                for (const shadowRoot of shadowRoots) {
                    macroEngine.observer.observe(shadowRoot, macroEngine.observerOptions);
                }
                if (shadowHostSelectors.size === 0) {
                    observer.disconnect();
                }
            });
            observer.observe(macroEngine.target, { childList: true, subtree: true });
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
            if (runningTours.has(tourName)) {
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
                if (tour.url && tour.url !== options.startUrl && options.redirect) {
                    window.location.href = window.location.origin + tour.url;
                }
            });
            if (!willUnload) {
                const shadow_doms = tour.steps.reduce((acc, step) => {
                    if (step.shadow_dom) {
                        acc.add(step.shadow_dom);
                    }
                    return acc;
                }, new Set());
                if (shadow_doms.size > 0) {
                    observeShadows(shadow_doms);
                }
                pointer.start();
                activateMacro(macro, options.mode);
            }
        }

        function resumeTour(tourName) {
            if (runningTours.has(tourName)) {
                return;
            }
            runningTours.add(tourName);
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

        function getSortedTours() {
            return Object.values(tours).sort((t1, t2) => {
                return t1.sequence - t2.sequence || (t1.name < t2.name ? -1 : 1);
            });
        }

        if (!window.frameElement) {
            // Resume running tours.
            for (const tourName of tourState.getActiveTourNames()) {
                if (tourName in tours) {
                    resumeTour(tourName);
                }
            }
        }

        odoo.startTour = startTour;
        odoo.isTourReady = (tourName) => tours[tourName].wait_for.then(() => true);

        // Auto start unconsumed tours if tour is not disabled and if the user is not on mobile.
        const isTourEnabled = "tour_disable" in session && !session.tour_disable;
        if (isTourEnabled && !ui.isSmall) {
            const sortedTours = getSortedTours().filter((tour) => !consumedTours.has(tour.name));
            for (const tour of sortedTours) {
                odoo.isTourReady(tour.name).then(() => {
                    startTour(tour.name, { mode: "manual", redirect: false });
                });
            }
        }

        return {
            bus,
            startTour,
            getSortedTours,
        };
    },
};

registry.category("services").add("tour_service", tourService);
