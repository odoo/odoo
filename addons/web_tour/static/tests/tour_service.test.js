/** @odoo-module native */

import { afterEach, beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import {
    clearRegistry,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { Macro } from "@web/core/utils/macro";
import { session } from "@web/session";
import { tourState } from "@web_tour/js/tour_state";

describe.current.tags("desktop");

const tourRegistry = registry.category("web_tour.tours");
let macro;

class Root extends Component {
    static components = {};
    static template = xml`<t><button class="button0">Button 0</button></t>`;
    static props = ["*"];
}

async function pump(times = 6) {
    for (let i = 0; i < times; i++) {
        await animationFrame();
        await advanceTime(265);
    }
}

beforeEach(() => {
    clearRegistry(tourRegistry);
    tourState.clear();
    patchWithCleanup(Macro.prototype, {
        start() {
            super.start(...arguments);
            macro = this;
        },
    });
});

afterEach(() => {
    macro?.stop();
    macro = undefined;
    tourState.clear();
    // `?tour=` is read by the service of every test in this shard, so a URL
    // one test set must not survive it.
    browser.location.search = "";
});

describe("resuming a tour the registry does not have yet", () => {
    test("a tour registered after the service started still resumes", async () => {
        tourState.setCurrentTour("late_tour");
        tourState.setCurrentConfig({ mode: "auto", stepDelay: 0 });
        tourState.setCurrentIndex(0);

        await mountWithCleanup(Root);
        expect(tourRegistry.contains("late_tour")).toBe(false);

        tourRegistry.add("late_tour", {
            steps: () => [
                {
                    trigger: ".button0",
                    run() {
                        expect.step("late tour ran");
                    },
                },
            ],
        });
        await pump();
        expect.verifySteps(["late tour ran"]);
    });

    test("a manual tour absent from this page keeps its state and stays quiet", async () => {
        patchWithCleanup(browser.console, {
            error: (msg) => expect.step(`error: ${msg}`),
        });
        patchWithCleanup(session, { tour_enabled: true });
        tourState.setCurrentTour("elsewhere_tour");
        tourState.setCurrentConfig({ mode: "manual", stepDelay: 0 });

        await mountWithCleanup(Root);
        await advanceTime(31000);
        await animationFrame();

        expect(tourState.getCurrentTour()).toBe("elsewhere_tour");
        expect.verifySteps([]);
    });

    test("a tour nobody can produce is reported and its state dropped", async () => {
        patchWithCleanup(browser.console, {
            error: (msg) => expect.step(`error: ${msg}`),
        });
        tourState.setCurrentTour("no_such_tour");
        tourState.setCurrentConfig({ mode: "auto", stepDelay: 0 });

        await mountWithCleanup(Root);
        await advanceTime(31000);
        await animationFrame();

        expect(tourState.getCurrentTour()).toBe(null);
        expect.verifySteps([
            'error: Tour "no_such_tour" was resumed but is registered nowhere' +
                " (web_tour.tours registry). Its saved state has been dropped.",
        ]);
    });
});

/**
 * The three ways a page can start a tour on load -- a `?tour=` param, a tour
 * left mid-run in localStorage, and `session.current_tour` -- are alternatives,
 * and the first two used to be two consecutive `if`s.
 */
describe("starting a tour from a ?tour= url param", () => {
    test("resumes the tour once, not twice", async () => {
        // The precondition is only "tours are already enabled for this user"
        // (`res_users.py`: any admin on a database without demo data). With
        // them *disabled* `startTour` awaits `switch_tour_enabled` before
        // writing the tour state, so the boot block that follows read no
        // current tour and the bug stayed hidden -- which is why no test saw
        // it. With them enabled, `startTour` runs synchronously through
        // `tourState.setCurrentTour(...)` and `resumeTour()` returns at its
        // own first `await`, so the next block found the state set and
        // resumed the SAME tour a second time, in the same task.
        patchWithCleanup(session, { tour_enabled: true });
        browser.location.search = "?tour=url_tour";
        onRpc("web_tour.tour", "get_tour_json_by_name", () => {
            expect.step("get_tour_json_by_name");
            return {
                name: "url_tour",
                steps: [{ trigger: ".button0", run: "click" }],
            };
        });

        // Mounting starts the services, so the whole boot block runs here.
        await mountWithCleanup(Root);
        // Pumped rather than given one frame: the resume loads the
        // `web_tour.interactive` bundle before it can mount a pointer, and
        // whether that bundle is already in the page depends on which suites
        // ran before this one.
        await pump();

        // Two fetches of the same tour is the visible half of the race; the
        // pointer count is the half that reaches the user -- measured at 0
        // before the fix, not 2: the two `TourInteractive` instances each ran
        // the step and each called `pointer.stop()`, so the tour a user opened
        // ended up with no pointer at all.
        expect.verifySteps(["get_tour_json_by_name"]);
        expect(".o_tour_pointer").toHaveCount(1);
    });

    test("wins over a tour left mid-run in localStorage", async () => {
        // Chaining the branches also answers "which tour wins?" when a
        // `?tour=` link is opened while stale state names another tour: the
        // URL. It won before too -- `startTour` overwrites the state either
        // way -- but only after the stale one had already been resumed
        // alongside it.
        patchWithCleanup(session, { tour_enabled: true });
        browser.location.search = "?tour=url_tour";
        tourState.setCurrentTour("stale_tour");
        tourState.setCurrentConfig({ mode: "manual", stepDelay: 0 });
        tourState.setCurrentIndex(0);
        tourRegistry.add("stale_tour", {
            steps: () => [
                {
                    trigger: ".button0",
                    run() {
                        expect.step("stale tour ran");
                    },
                },
            ],
        });
        onRpc("web_tour.tour", "get_tour_json_by_name", ({ args }) => {
            expect.step(`fetched ${args[0]}`);
            return {
                name: "url_tour",
                steps: [{ trigger: ".button0", run: "click" }],
            };
        });

        await mountWithCleanup(Root);
        await pump();

        expect.verifySteps(["fetched url_tour"]);
        expect(tourState.getCurrentTour()).toBe("url_tour");
    });
});
