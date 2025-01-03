/** @odoo-module **/

import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { getService, makeMockEnv, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { tourState } from "@web_tour/tour_service/tour_state";

describe.current.tags("desktop");

const tourRegistry = registry.category("web_tour.tours");

test("Step Tour validity", async () => {
    patchWithCleanup(console, {
        error: (msg) => expect.step(msg),
    });
    const steps = [
        {
            Belgium: true,
            wins: "of course",
            EURO2024: true,
            trigger: "button.foo",
        },
        {
            my_title: "EURO2024",
            trigger: "button.bar",
            doku: "Lukaku 10",
        },
        {
            trigger: "button.bar",
            run: ["Enjoy euro 2024"],
        },
        {
            trigger: "button.bar",
            run() {},
        },
    ];
    tourRegistry.add("tour1", {
        steps: () => steps,
    });
    await makeMockEnv({});
    const waited_error1 = `Error in schema for TourStep ${JSON.stringify(
        steps[0],
        null,
        4
    )}\nInvalid object: unknown key 'Belgium', unknown key 'wins', unknown key 'EURO2024'`;
    const waited_error2 = `Error in schema for TourStep ${JSON.stringify(
        steps[1],
        null,
        4
    )}\nInvalid object: unknown key 'my_title', unknown key 'doku'`;
    const waited_error3 = `Error in schema for TourStep ${JSON.stringify(
        steps[2],
        null,
        4
    )}\nInvalid object: 'run' is not a string or function or boolean`;
    await getService("tour_service").startTour("tour1");
    await animationFrame();
    expect.verifySteps([waited_error1, waited_error2, waited_error3]);
});

test("override existing tour by using saveAs", async () => {
    tourRegistry
        .add("Tour 1", {
            steps: () => [{ trigger: "#1" }],
            saveAs: "homepage",
        })
        .add("Tour 2", {
            steps: () => [{ trigger: "#2" }],
            saveAs: "homepage",
        });
    await makeMockEnv({});
    await getService("tour_service").startTour("homepage");
    await animationFrame();
    expect(tourState.getCurrentTour()).toBe("Tour 2");
});
