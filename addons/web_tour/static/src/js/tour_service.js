/** @odoo-module native */
import { Component, markup, validate, whenReady } from "@odoo/owl";
import { DropdownItem } from "@web/components/dropdown";
import { loadBundle } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { translationIsReady } from "@web/core/translation";
import { redirect } from "@web/core/utils/urls";
import { session } from "@web/session";
import { createPointerState } from "@web_tour/js/tour_pointer/tour_pointer_state";
import {
    TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY,
    tourRecorderState,
} from "@web_tour/js/tour_recorder/tour_recorder_state";
import { tourState } from "@web_tour/js/tour_state";
import { callWithUnloadCheck } from "@web_tour/js/utils/tour_utils";

import DOMPurify from "dompurify";

const AUTOMATIC_ENTRY = "@web_tour/js/tour_automatic/tour_automatic";

function loadAutomaticRuntime() {
    if (odoo.loader?.modules?.has(AUTOMATIC_ENTRY)) {
        return Promise.resolve();
    }
    return loadBundle("web_tour.automatic", { css: false });
}

class OnboardingItem extends Component {
    static components = { DropdownItem };
    static template = "web_tour.OnboardingItem";
    static props = {
        toursEnabled: { type: Boolean },
        toggleItem: { type: Function },
    };
    setup() {}
}

const StepSchema = {
    id: { type: [String], optional: true },
    content: { type: [String, Object], optional: true },
    debugHelp: { type: String, optional: true },
    isActive: { type: Array, element: String, optional: true },
    run: { type: [String, Function, Boolean], optional: true },
    timeout: {
        optional: true,
        validate(value) {
            return value >= 0 && value <= 60000;
        },
    },
    tooltipPosition: {
        optional: true,
        validate(value) {
            return ["top", "bottom", "left", "right"].includes(value);
        },
    },
    trigger: { type: String },
    expectUnloadPage: { type: Boolean, optional: true },
    pause: { type: Boolean, optional: true },
    break: { type: Boolean, optional: true },
};

const TourSchema = {
    name: { type: String, optional: true },
    steps: Function,
    timeout: {
        optional: true,
        validate(value) {
            return value >= 0 && value <= 60000;
        },
    },
    url: { type: String, optional: true },
    wait_for: { type: [Function, Object], optional: true },
};

registry.category("web_tour.tours").addValidation(TourSchema);
const debugMenuRegistry = registry.category("debug").category("default");

const TOUR_REGISTRATION_TIMEOUT = 30000;

export const tourService = {
    dependencies: ["orm", "effect", "overlay", "localization"],
    start: async (env, { orm, effect, overlay }) => {
        await whenReady();
        let toursEnabled = session?.tour_enabled;
        const tourRegistry = registry.category("web_tour.tours");
        const pointer = createPointerState();
        pointer.stop = () => {};

        debugMenuRegistry.add("onboardingItem", () => ({
            type: "component",
            Component: OnboardingItem,
            props: {
                toursEnabled: toursEnabled || false,
                toggleItem: async () => {
                    tourState.clear();
                    toursEnabled = await orm.call("res.users", "switch_tour_enabled", [
                        !toursEnabled,
                    ]);
                    browser.location.reload();
                },
            },
            sequence: 500,
            section: "testing",
        }));

        function getTourFromRegistry(tourName) {
            if (!tourRegistry.contains(tourName)) {
                return;
            }
            const tour = tourRegistry.get(tourName);
            return {
                ...tour,
                steps: tour.steps(),
                name: tourName,
                wait_for: tour.wait_for || Promise.resolve(),
            };
        }

        async function getTourFromDB(tourName) {
            const tour = await orm.call("web_tour.tour", "get_tour_json_by_name", [
                tourName,
            ]);
            if (!tour) {
                throw new Error(`Tour '${tourName}' is not found in the database.`);
            }

            if (!tour.steps.length && tourRegistry.contains(tour.name)) {
                tour.steps = tourRegistry.get(tour.name).steps();
            }

            return tour;
        }

        function validateStep(step) {
            try {
                validate(step, StepSchema);
            } catch (error) {
                console.error(
                    `Error in schema for TourStep ${JSON.stringify(step, null, 4)}\n${
                        error.message
                    }`,
                );
            }
        }

        async function startTour(tourName, options = {}) {
            pointer.stop();
            const tourFromRegistry = getTourFromRegistry(tourName);

            if (!tourFromRegistry && !options.fromDB) {
                return;
            }

            const tour = options.fromDB
                ? { name: tourName, url: options.url }
                : tourFromRegistry;
            if (!session.is_public && !toursEnabled && options.mode === "manual") {
                toursEnabled = await orm.call("res.users", "switch_tour_enabled", [
                    !toursEnabled,
                ]);
            }

            let tourConfig = {
                delayToCheckUndeterminisms: 0,
                stepDelay: 0,
                keepWatchBrowser: false,
                mode: "auto",
                showPointerDuration: 0,
                debug: false,
                redirect: true,
            };

            tourConfig = Object.assign(tourConfig, options);
            tourState.setCurrentConfig(tourConfig);
            tourState.setCurrentTour(tour.name);
            tourState.setCurrentIndex(0);

            const willUnload = callWithUnloadCheck(() => {
                if (
                    tour.url &&
                    tourConfig.startUrl !== tour.url &&
                    tourConfig.redirect
                ) {
                    redirect(tour.url);
                }
            });
            if (!willUnload) {
                await resumeTour();
            }
        }

        function whenTourIsRegistered(tourName, timeout = TOUR_REGISTRATION_TIMEOUT) {
            if (tourRegistry.contains(tourName)) {
                return Promise.resolve(true);
            }
            return new Promise((resolve) => {
                let timer;
                const onUpdate = (ev) => {
                    if (ev.detail.key !== tourName) {
                        return;
                    }
                    browser.clearTimeout(timer);
                    tourRegistry.removeEventListener("UPDATE", onUpdate);
                    resolve(true);
                };
                timer = browser.setTimeout(() => {
                    tourRegistry.removeEventListener("UPDATE", onUpdate);
                    resolve(false);
                }, timeout);
                tourRegistry.addEventListener("UPDATE", onUpdate);
            });
        }

        async function resumeTour() {
            const tourName = tourState.getCurrentTour();
            const tourConfig = tourState.getCurrentConfig();

            let tour;
            if (tourConfig.fromDB) {
                tour = await getTourFromDB(tourName);
            } else {
                tour = getTourFromRegistry(tourName);
                if (!tour) {
                    await whenTourIsRegistered(tourName);
                    tour = getTourFromRegistry(tourName);
                }
            }
            if (!tour) {
                if (tourConfig.mode !== "auto") {
                    return;
                }
                tourState.clear();
                browser.console.error(
                    `Tour "${tourName}" was resumed but is registered nowhere` +
                        ` (${tourConfig.fromDB ? "database" : "web_tour.tours registry"}).` +
                        " Its saved state has been dropped.",
                );
                return;
            }

            tour.steps.forEach((step) => validateStep(step));

            if (tourConfig.mode === "auto") {
                await loadAutomaticRuntime();
                const { TourAutomatic } =
                    await import("@web_tour/js/tour_automatic/tour_automatic");
                new TourAutomatic(tour).start();
            } else {
                await loadBundle("web_tour.interactive");
                const { TourPointer } =
                    await import("@web_tour/js/tour_pointer/tour_pointer");
                pointer.stop = overlay.add(
                    TourPointer,
                    {
                        pointerState: pointer.state,
                        bounce: !(
                            tourConfig.mode === "auto" && tourConfig.keepWatchBrowser
                        ),
                    },
                    {
                        sequence: 1100,
                    },
                );
                const { TourInteractive } =
                    await import("@web_tour/js/tour_interactive/tour_interactive");
                new TourInteractive(tour).start(env, pointer, async () => {
                    pointer.stop();
                    tourState.clear();
                    browser.console.log("tour succeeded");
                    let message =
                        tourConfig.rainbowManMessage || tour.rainbowManMessage;
                    if (message) {
                        message = DOMPurify.sanitize(tourConfig.rainbowManMessage);
                        effect.add({
                            type: "rainbow_man",
                            message: markup(message),
                        });
                    }

                    const nextTour = await orm.call("web_tour.tour", "consume", [
                        tour.name,
                    ]);
                    if (nextTour) {
                        startTour(nextTour.name, {
                            mode: "manual",
                            redirect: false,
                            rainbowManMessage: nextTour.rainbowManMessage,
                        });
                    }
                });
            }
        }

        async function tourRecorder() {
            await loadBundle("web_tour.recorder");
            const { TourRecorder } =
                await import("@web_tour/js/tour_recorder/tour_recorder");
            const remove = overlay.add(
                TourRecorder,
                {
                    onClose: () => {
                        remove();
                        browser.localStorage.removeItem(
                            TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY,
                        );
                        tourRecorderState.clear();
                    },
                },
                { sequence: 99999 },
            );
        }

        async function startTourRecorder() {
            if (!browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY)) {
                await tourRecorder();
            }
            browser.localStorage.setItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY, "1");
        }

        if (!window.frameElement) {
            const paramsTourName = new URLSearchParams(browser.location.search).get(
                "tour",
            );
            // `else if`, not a second `if`: a `?tour=` param already owns the
            // resume, and this block used to run it a SECOND time for the same
            // tour, concurrently. `startTour` only reaches an `await` before it
            // writes the tour state when tours are *disabled* for the user (the
            // `switch_tour_enabled` call above); with them already enabled its
            // body runs synchronously through `tourState.setCurrentTour(...)`
            // and into `resumeTour()`, which itself returns at its own first
            // `await`. So control came back here with `getCurrentTour()`
            // already set, and -- `toursEnabled` being true -- this block
            // called `resumeTour()` again in the same task, with nothing in
            // `resumeTour` guarding re-entrancy: two `TourInteractive`
            // instances and two `overlay.add(TourPointer, ...)` for one tour.
            // Chaining the branches also settles which tour wins when a
            // `?tour=` link is opened while a stale `current_tour` sits in
            // localStorage: the URL, whose state `startTour` overwrites anyway.
            if (paramsTourName) {
                startTour(paramsTourName, { mode: "manual", fromDB: true });
            } else if (tourState.getCurrentTour()) {
                if (tourState.getCurrentConfig().mode === "auto" || toursEnabled) {
                    resumeTour();
                } else {
                    tourState.clear();
                }
            } else if (session.current_tour) {
                startTour(session.current_tour.name, {
                    mode: "manual",
                    redirect: false,
                    rainbowManMessage: session.current_tour.rainbowManMessage,
                });
            }

            if (
                browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY) &&
                !session.is_public
            ) {
                await tourRecorder();
            }
        }

        odoo.startTour = startTour;
        odoo.isTourReady = (tourName) => {
            if (!tourRegistry.contains(tourName)) {
                return false;
            }
            const tour = tourRegistry.get(tourName);
            return Promise.all([
                translationIsReady,
                tour.wait_for || Promise.resolve(),
                loadAutomaticRuntime(),
            ]).then(() => true);
        };

        return {
            startTour,
            startTourRecorder,
        };
    },
};

registry.category("services").add("tour_service", tourService);
