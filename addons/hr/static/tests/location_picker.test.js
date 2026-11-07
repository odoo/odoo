import { animationFrame, beforeEach, describe, expect, mockPermission, test } from "@odoo/hoot";
import {
    contains,
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { assets, AssetsLoadingError } from "@web/core/assets";
import { WebClient } from "@web/webclient/webclient";

import { defineHrModels } from "@hr/../tests/hr_test_helpers";
import { HrWorkLocation } from "@hr/../tests/mock_server/mock_models/hr_work_location";

describe.current.tags("desktop");
defineHrModels();

/** The maps created by the picker, from a fake Leaflet recording what is done with them */
let maps;

beforeEach(() => {
    HrWorkLocation._records = [
        { id: 1, name: "Brussels Office", location_type: "office", latitude: 0, longitude: 0 },
    ];
    maps = [];
    patchWithCleanup(assets, {
        loadJS: async () => {},
        loadCSS: async () => {},
    });
    patchWithCleanup(window, {
        L: {
            map() {
                const map = {
                    handlers: {},
                    on(event, handler) {
                        this.handlers[event] = handler;
                        return this;
                    },
                    setView([lat, lng]) {
                        expect.step(`view ${lat}, ${lng}`);
                        return this;
                    },
                    remove() {},
                };
                maps.push(map);
                return map;
            },
            tileLayer() {
                return { addTo: () => {} };
            },
            marker([lat, lng]) {
                expect.step(`marker ${lat}, ${lng}`);
                return {
                    addTo() {
                        return this;
                    },
                    setLatLng([lat, lng]) {
                        expect.step(`marker ${lat}, ${lng}`);
                    },
                };
            },
        },
    });
    onRpc("hr.work.location", "write", ({ args }) => {
        expect.step(`write ${JSON.stringify(args)}`);
    });
});

async function openLocationPicker(context) {
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        type: "ir.actions.client",
        tag: "open_location_map",
        target: "new",
        name: "Set Location Coordinates",
        context: { location_res_id: 1, footer: false, ...context },
    });
}

test("location picker of a work location with coordinates", async () => {
    await openLocationPicker({ location_latitude: 50.8503, location_longitude: 4.3517 });

    expect(".o_hr_location_picker form[role=search]").toHaveCount(1);
    expect(".o_hr_location_picker .o_workplace_map").toHaveCount(1);
    expect.verifySteps(["view 50.8503, 4.3517", "marker 50.8503, 4.3517"]);

    await contains(".o_hr_location_picker .btn-primary:contains(Set)").click();
    expect.verifySteps(['write [[1],{"latitude":50.8503,"longitude":4.3517}]']);
    expect(".o_hr_location_picker").toHaveCount(0);
});

test("location picker of a work location without coordinates", async () => {
    // Without coordinates nor access to the position of the device, there is nothing to show
    await openLocationPicker({ location_latitude: 0, location_longitude: 0 });
    expect(".o_hr_location_picker .o_workplace_map").toHaveCount(0);
    expect(".o_hr_location_picker").toHaveText(/Unable to access Location/);
    expect.verifySteps([]);
});

test("location picker without coordinates, with the position of the device", async () => {
    mockPermission("geolocation", "granted");
    await openLocationPicker({ location_latitude: 0, location_longitude: 0 });
    expect(".o_hr_location_picker .o_workplace_map").toHaveCount(1);

    // Nothing selected yet: nothing to save
    await contains(".o_hr_location_picker .btn-primary:contains(Set)").click();
    expect(".o_notification:contains(Please select a location)").toHaveCount(1);
    expect.verifySteps([]);
});

test("location picker: select a location on the map", async () => {
    await openLocationPicker({ location_latitude: 50.8503, location_longitude: 4.3517 });
    expect.verifySteps(["view 50.8503, 4.3517", "marker 50.8503, 4.3517"]);

    maps[0].handlers.click({ latlng: { lat: 50.8467, lng: 4.3525 } });
    await animationFrame();
    expect.verifySteps(["marker 50.8467, 4.3525", "view 50.8467, 4.3525"]);

    await contains(".o_hr_location_picker .btn-primary:contains(Set)").click();
    expect.verifySteps(['write [[1],{"latitude":50.8467,"longitude":4.3525}]']);
});

test("location picker: search an address", async () => {
    onRpc("base.geocoder", "geo_find", ({ args }) => {
        expect.step(`geo_find ${args[0]}`);
        return [50.8467, 4.3525];
    });
    await openLocationPicker({ location_latitude: 50.8503, location_longitude: 4.3517 });
    expect.verifySteps(["view 50.8503, 4.3517", "marker 50.8503, 4.3517"]);

    await contains(".o_hr_location_picker input.search-query").edit("Grand-Place, Brussels", {
        confirm: false,
    });
    await contains(".o_hr_location_picker button[type=submit]").click();
    expect.verifySteps([
        "geo_find Grand-Place, Brussels",
        "marker 50.8467, 4.3525",
        "view 50.8467, 4.3525",
    ]);

    await contains(".o_hr_location_picker .btn-primary:contains(Set)").click();
    expect.verifySteps(['write [[1],{"latitude":50.8467,"longitude":4.3525}]']);
});

test("location picker: search coordinates", async () => {
    onRpc("base.geocoder", "geo_find", () => {
        expect.step("geo_find");
        return false;
    });
    await openLocationPicker({ location_latitude: 50.8503, location_longitude: 4.3517 });
    expect.verifySteps(["view 50.8503, 4.3517", "marker 50.8503, 4.3517"]);

    // The coordinates are selected as such, without the geocoder
    await contains(".o_hr_location_picker input.search-query").edit("-33.8568, 151.2153", {
        confirm: false,
    });
    await contains(".o_hr_location_picker button[type=submit]").click();
    expect.verifySteps(["marker -33.8568, 151.2153", "view -33.8568, 151.2153"]);

    // Out of bounds
    await contains(".o_hr_location_picker input.search-query").edit("95, 4.35", { confirm: false });
    await contains(".o_hr_location_picker button[type=submit]").click();
    expect(".o_notification:contains(The latitude must be between -90 and 90)").toHaveCount(1);
    expect.verifySteps([]);

    await contains(".o_hr_location_picker .btn-primary:contains(Set)").click();
    expect.verifySteps(['write [[1],{"latitude":-33.8568,"longitude":151.2153}]']);
});

test("location picker in readonly", async () => {
    await openLocationPicker({
        location_latitude: 50.8503,
        location_longitude: 4.3517,
        location_readonly: true,
    });
    expect.verifySteps(["view 50.8503, 4.3517", "marker 50.8503, 4.3517"]);
    expect(".o_hr_location_picker form[role=search]").toHaveCount(0);
    expect(".o_hr_location_picker .btn-primary:contains(Set)").toHaveCount(0);
    expect(maps[0].handlers.click).toBe(undefined);

    await contains(".o_hr_location_picker .btn-primary:contains(Close)").click();
    expect(".o_hr_location_picker").toHaveCount(0);
    expect.verifySteps([]);
});

test("location picker when the map can't be loaded", async () => {
    patchWithCleanup(assets, {
        loadJS: async () => {
            throw new AssetsLoadingError("Leaflet unavailable");
        },
    });
    await openLocationPicker({ location_latitude: 50.8503, location_longitude: 4.3517 });
    expect(".o_hr_location_picker").toHaveText(/There was an error loading the map/);
    expect(".o_hr_location_picker .o_workplace_map").toHaveCount(0);
    expect.verifySteps([]);
});
