import { EventBus, reactive } from "@odoo/owl";

import { config as transitionConfig } from "@web/core/transition";
import { session } from "@web/session";
import { MacroedTour } from "./macroed_tour";
import { tourState } from "./tour_state";
import { callWithUnloadCheck } from "./tour_utils";
import { MacroEngine } from "@web/core/macro";
import { createPointerState } from "./tour_pointer_state";
import { browser } from "@web/core/browser/browser";

export class TourRunner {

    constructor() {
        this.runningTours = new Set();
        this.tours = {};
        this.consumedTours = new Set(session.web_tours);
        this.macroEngine = new MacroEngine({ target: document });
        this.bus = new EventBus();
        this.pointers = reactive({});
        this.toursEnabled = "tour_disable" in session && !session.tour_disable;
        this.possiblePointTos = [];
    }

    startTour(tourName, options = {}) {
        debugger;
        if (!options.force && this.runningTours.has(tourName) && options.mode === "manual") {
            return;
        }
        const tour = this.tours[tourName];
        if (!tour) {
            throw new Error(`Tour '${tourName}' is not found.`);
        }
        this.runningTours.add(tourName);
        const runOptions = {
            stepDelay: 0,
            keepWatchBrowser: false,
            mode: "auto",
            startUrl: "",
            showPointerDuration: 0,
            redirect: true,
            ...options
        };
        tourState.set(tourName, "currentIndex", 0);
        tourState.set(tourName, "stepDelay", runOptions.stepDelay);
        tourState.set(tourName, "keepWatchBrowser", runOptions.keepWatchBrowser);
        tourState.set(tourName, "showPointerDuration", runOptions.showPointerDuration);
        tourState.set(tourName, "mode", runOptions.mode);
        tourState.set(tourName, "sequence", tour.sequence);
        const pointer = this.createPointer(tourName, {
            bounce: !(options.mode === "auto" && options.keepWatchBrowser),
        });
        runOptions.pointer = pointer;
        tour.resetRun(runOptions)
        const willUnload = callWithUnloadCheck(() => {
            if (tour.url && tour.url !== options.startUrl && options.redirect) {
                const search = new URLSearchParams(window.location.search);
                const toUrl = new URL(window.location.origin + tour.url);
                toUrl.searchParams.set("debug", search.get("debug"))
                window.location.href = toUrl.href;
            }
        });
        if (!willUnload) {
            if (tour.shadowSelectors && tour.shadowSelectors.size > 0) {
                this.observeShadows(tour.shadowSelectors);
            }
            pointer.start();
            this.activateMacro(tour, runOptions.mode);
        }
    }

    resumeTour(tourName) {
        if (this.runningTours.has(tourName)) {
            return;
        }
        this.runningTours.add(tourName);
        const tour = this.tours[tourName];
        const stepDelay = tourState.get(tourName, "stepDelay");
        const keepWatchBrowser = tourState.get(tourName, "keepWatchBrowser");
        const showPointerDuration = tourState.get(tourName, "showPointerDuration");
        const startIndex = tourState.get(tour.name, "currentIndex");
        const mode = tourState.get(tourName, "mode");
        const pointer = this.createPointer(tourName, {
            bounce: !(mode === "auto" && keepWatchBrowser),
        });
        const runOptions = {
            startIndex,
            mode,
            stepDelay,
            keepWatchBrowser,
            showPointerDuration,
            pointer,
        }
        tour.resetRun(runOptions)
        pointer.start();
        this.activateMacro(tour, mode);
    }
    
    register(name, tourDescription) {
        name = tourDescription.saveAs || name;
        const tourDescr = {
            name,
            wait_for: Promise.resolve(),
            fadeout: "medium",
            sequence: 1000,
            ...tourDescription,
        }
        const tour = new MacroedTour(tourDescr, {
            onStepConsummed: this.onStepConsummed.bind(this),
            onTourEnd: this.onTourEnd.bind(this),
        });
        this.tours[name] = tour;
        tour.wait_for.then(() => {
            if (
                !tour.test &&
                this.toursEnabled &&
                !this.consumedTours.has(name) &&
                !tourState.getActiveTourNames().includes(name)
            ) {
                this.startTour(name, { mode: "manual", redirect: false });
            }
        });
    }
    activateMacro(macro, mode) {
        if (mode === "auto") {
            transitionConfig.disabled = true;
        }
        this.macroEngine.activate(macro, mode === "auto");
    }

    onStepConsummed(tour, step) {
        this.bus.trigger("STEP-CONSUMMED", { tour, step });
    }

    onTourEnd(tour) {
        this.bus.trigger("TOUR_END", tour);
        const { mode, name } = tour;
        if (mode === "manual") {
            this.consumedTours.add(name);
        }
        // Used to signal the python test runner that the tour finished without error.
        browser.console.log("tour succeeded");
        this.runningTours.delete(name);
    }

    /**
 * Wait for the shadow hosts matching the given selectors to
 * appear in the DOM then, register the underlying shadow roots
 * to the macro engine observer in order to listen to the
 * changes in the shadow DOM.
 *
 * @param {Set<string>} shadowHostSelectors
 */
    observeShadows(shadowHostSelectors) {
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
                this.macroEngine.observer.observe(shadowRoot, macroEngine.observerOptions);
            }
            if (shadowHostSelectors.size === 0) {
                observer.disconnect();
            }
        });
        observer.observe(this.macroEngine.target, { childList: true, subtree: true });
    }

    createPointer(tourName, config) {
        const pointers = this.pointers;
        const { state: pointerState, methods } = createPointerState();
        const bus = this.bus;
        const possiblePointTos = this.possiblePointTos;
        return {
            start() {
                pointers[tourName] = {
                    methods,
                    id: tourName,
                    props: { pointerState, ...config },
                };
                bus.trigger("POINTER_CHANGE", { operation: "add", pointer: pointers[tourName] })
            },
            stop() {
                bus.trigger("POINTER_CHANGE", { operation: "remove", pointer: pointers[tourName] })
                delete pointers[tourName];
                methods.destroy();
            },
            ...methods,
            async pointTo(anchor, step) {
                possiblePointTos.push([tourName, () => methods.pointTo(anchor, step)]);
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
            }
        }
    }
}

export const runner = new TourRunner();

export function getSortedTours() {
    return Object.values(runner.tours).sort((t1, t2) => {
        return t1.sequence - t2.sequence || (t1.name < t2.name ? -1 : 1);
    });
}
