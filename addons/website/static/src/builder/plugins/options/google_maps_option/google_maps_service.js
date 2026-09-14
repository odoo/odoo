/** @odoo-module native */
import { registry } from "@web/core/registry";
import { createGoogleMapsService } from "@website/utils/google_maps";

registry.category("services").add("google_maps", {
    dependencies: ["notification"],
    start(env, { notification }) {
        const service = createGoogleMapsService(notification);
        return {
            getGMapsAPIKey: service.getGMapAPIKey,
            loadGMapsAPI(editableMode, refetch) {
                // Calls inside the shared implementation must still reach
                // overrides on this service's public, plural-named API.
                return service.loadGMapAPI.call(
                    { getGMapAPIKey: (...args) => this.getGMapsAPIKey(...args) },
                    editableMode,
                    refetch,
                );
            },
            validateGMapsApiKey(key) {
                return service.validateGMapApiKey.call(
                    { fetchGoogleMap: (key) => this.fetchGoogleMaps(key) },
                    key,
                );
            },
            fetchGoogleMaps: service.fetchGoogleMap,
        };
    },
});
