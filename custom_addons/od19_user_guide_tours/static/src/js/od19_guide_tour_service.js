import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";

/**
 * OD19 User Guide — app scoped auto start.
 *
 * Core `web_tour` only knows about a single *sequential* onboarding queue:
 * `web_tour.tour.get_current_tour()` returns the first tour with
 * `custom = False` that the user has not consumed yet, whatever the
 * application currently opened. As a consequence a user could only ever see
 * one onboarding tour at a time, in a fixed order, and the guide tours never
 * popped up on their own.
 *
 * This service changes that behaviour without touching the core:
 *  - `web_tour.tour.od19_guide_get_app_tours()` gives the mapping
 *    "application root menu" -> "guide tour";
 *  - every time the user opens an application (`MENUS:APP-CHANGED`) the tour
 *    registered for that application is started, so entering *any* module for
 *    the first time shows its tour right away;
 *  - switching applications always starts the tour of the application that is
 *    being opened, even if the previous guide tour was left unfinished;
 *  - a tour is remembered as seen only once the user **completes** it: the
 *    consumption is left to the core (`web_tour.tour.consume`, called by
 *    `tour_service` when the interactive tour succeeds). An unfinished tour is
 *    therefore proposed again the next time the application is opened, instead
 *    of being silently lost after its first display.
 *
 * On the server side `web_tour.tour.get_current_tour()` is overridden so that
 * the core sequential queue stays silent while the user still has a guide tour
 * to discover.
 */
const START_DELAY = 1200;

export const od19GuideTourService = {
    dependencies: ["orm", "menu", "tour_service"],

    async start(env, { orm, menu, tour_service }) {
        /** @type {{menuId: number, tourName: string, consumed: boolean}[]} */
        let appTours = [];
        const startedThisPage = new Set();

        const loadMapping = async () => {
            try {
                appTours = await orm.call("web_tour.tour", "od19_guide_get_app_tours", []);
            } catch {
                appTours = [];
            }
        };

        const maybeStart = async () => {
            const app = menu.getCurrentApp();
            if (!app) {
                return;
            }
            const entry = appTours.find((item) => item.menuId === app.id);
            if (!entry || entry.consumed || startedThisPage.has(entry.tourName)) {
                return;
            }
            startedThisPage.add(entry.tourName);
            try {
                await tour_service.startTour(entry.tourName, {
                    mode: "manual",
                    fromDB: true,
                    redirect: false,
                });
            } catch {
                // The tour is not part of this build: nothing to show.
            }
            // The tour stays un-consumed here on purpose: the core marks it as
            // seen only when the user reaches the last step (`web_tour.tour.consume`
            // called by `tour_service`). A tour that never shows up — or that the
            // user leaves unfinished — is proposed again the next time the
            // application is opened.
        };

        const schedule = () => {
            browser.setTimeout(maybeStart, START_DELAY);
        };

        await loadMapping();
        env.bus.addEventListener("MENUS:APP-CHANGED", schedule);
        schedule();
    },
};

registry.category("services").add("od19_guide_tour_service", od19GuideTourService);
