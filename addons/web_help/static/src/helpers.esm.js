/** @odoo-module **/
import {registry} from "@web/core/registry";
import {Component} from "@odoo/owl";

export async function findTrip(model, viewType) {
    const trips = registry.category("trips").getAll();
    const selectorResults = await Promise.all(
        trips.map((trip) => trip.selector(model, viewType))
    );
    const matchedTrips = trips.filter((trip, i) => selectorResults[i]);
    if (matchedTrips.length >= 1) {
        if (matchedTrips.length != 1) {
            console.warn("More than one trip found", model, viewType);
        }
        return matchedTrips[0].Trip;
    }
    return null;
}

export function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function waitUntilAvailable(selector, ms = 50) {
    const selection = $(selector);

    if (!selection.length) {
        await wait(ms);
        return await waitUntilAvailable(selector, ms);
    }

    return selection;
}

export async function doAction(xmlId, options = {}) {
    Component.env.bus.trigger("do-action", {
        action: xmlId,
        options: options,
    });
}
