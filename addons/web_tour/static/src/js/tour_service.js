import { Component, markup, whenReady, validate, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { TourPointer } from "@web_tour/js/tour_pointer/tour_pointer";
import { createPointerState } from "@web_tour/js/tour_pointer/tour_pointer_state";
import { tourState } from "@web_tour/js/tour_state";
import { TourInteractive } from "@web_tour/js/tour_interactive/tour_interactive";
import { TourAutomatic } from "@web_tour/js/tour_automatic/tour_automatic";
import { callWithUnloadCheck } from "@web_tour/js/utils/tour_utils";
import {
    TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY,
    TourRecorder,
} from "@web_tour/js/tour_recorder/tour_recorder";
import { redirect } from "@web/core/utils/urls";
import { tourRecorderState } from "@web_tour/js/tour_recorder/tour_recorder_state";

class OnboardingItem extends Component {
    static components = { DropdownItem };
    static template = xml`
    <DropdownItem>
        <div class="d-flex justify-content-between ps-3">
            <div class="align-self-center">
                <span class="form-check form-switch" t-on-click.stop.prevent="() => this.props.toggleItem()">
                    <input type="checkbox" class="form-check-input" id="onboarding" t-att-checked="this.props.toursEnabled"/>
                    <label class="form-check-label">Onboarding</label>
                </span>
            </div>
        </div>
    </DropdownItem>
    `;
    static props = {
        toursEnabled: { type: Boolean },
        toggleItem: { type: Function },
    };
    setup() {}
}

const StepSchema = {
    id: { type: [String], optional: true },
    content: { type: [String, Object], optional: true }, //allow object(_t && markup)
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
    //ONLY IN DEBUG MODE
    pause: { type: Boolean, optional: true },
    break: { type: Boolean, optional: true },
};

const TourSchema = {
    name: { type: String, optional: true },
    steps: Function,
    url: { type: String, optional: true },
    wait_for: { type: [Function, Object], optional: true },
};

registry.category("web_tour.tours").addValidation(TourSchema);
const debugMenuRegistry = registry.category("debug").category("default");

export const tourService = {
    // localization dependency to make sure translations used by tours are loaded
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
            const tour = await orm.call("web_tour.tour", "get_tour_json_by_name", [tourName]);
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
                    }`
                );
            }
        }

        async function startTour(tourName, options = {}) {
            pointer.stop();
            const tourFromRegistry = getTourFromRegistry(tourName);

            if (!tourFromRegistry && !options.fromDB) {
                // Sometime tours are not loaded depending on the modules.
                // For example, point_of_sale do not load all tours assets.
                return;
            }

            const tour = options.fromDB ? { name: tourName, url: options.url } : tourFromRegistry;
            if (!session.is_public && !toursEnabled && options.mode === "manual") {
                toursEnabled = await orm.call("res.users", "switch_tour_enabled", [!toursEnabled]);
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
                if (tour.url && tourConfig.startUrl != tour.url && tourConfig.redirect) {
                    redirect(tour.url);
                }
            });
            if (!willUnload) {
                resumeTour();
            }
        }

        async function resumeTour() {
            const tourName = tourState.getCurrentTour();
            const tourConfig = tourState.getCurrentConfig();

            let tour = getTourFromRegistry(tourName);
            if (tourConfig.fromDB) {
                tour = await getTourFromDB(tourName);
            }
            if (!tour) {
                return;
            }

            tour.steps.forEach((step) => validateStep(step));
            pointer.stop = overlay.add(
                TourPointer,
                {
                    pointerState: pointer.state,
                    bounce: !(tourConfig.mode === "auto" && tourConfig.keepWatchBrowser),
                },
                {
                    sequence: 1100, // sequence based on bootstrap z-index values.
                }
            );

            if (tourConfig.mode === "auto") {
                new TourAutomatic(tour).start();
            } else {
                new TourInteractive(tour).start(pointer, async () => {
                    pointer.stop();
                    tourState.clear();
                    browser.console.log("tour succeeded");
                    let message = tourConfig.rainbowManMessage || tour.rainbowManMessage;
                    if (message) {
                        message = window.DOMPurify.sanitize(tourConfig.rainbowManMessage);
                        effect.add({
                            type: "rainbow_man",
                            message: markup(message),
                        });
                    }

                    const nextTour = await orm.call("web_tour.tour", "consume", [tour.name]);
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

        function startTourRecorder() {
            if (!browser.localStorage.getItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY)) {
                const remove = overlay.add(
                    TourRecorder,
                    {
                        onClose: () => {
                            remove();
                            browser.localStorage.removeItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY);
                            tourRecorderState.clear();
                        },
                    },
                    { sequence: 99999 }
                );
            }
            browser.localStorage.setItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY, "1");
        }

        if (!window.frameElement) {
            const paramsTourName = new URLSearchParams(browser.location.search).get("tour");
            if (paramsTourName) {
                startTour(paramsTourName, { mode: "manual", fromDB: true });
            }

            if (tourState.getCurrentTour()) {
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
                const remove = overlay.add(
                    TourRecorder,
                    {
                        onClose: () => {
                            remove();
                            browser.localStorage.removeItem(TOUR_RECORDER_ACTIVE_LOCAL_STORAGE_KEY);
                            tourRecorderState.clear();
                        },
                    },
                    { sequence: 99999 }
                );
            }
        }

        odoo.startTour = startTour;
        odoo.isTourReady = (tourName) => getTourFromRegistry(tourName).wait_for.then(() => true);

        return {
            startTour,
            startTourRecorder,
        };
    },
};

registry.category("services").add("tour_service", tourService);
