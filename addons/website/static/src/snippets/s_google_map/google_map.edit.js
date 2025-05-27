/* global google */

import { GoogleMap } from "./google_map";
import { registry } from "@web/core/registry";

const GoogleMapEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            this.canSpecifyKey = true;
            this.websiteEditService = this.services.website_edit;
            this.websiteMapService = this.services.website_map;
        }

        async willStart() {
            const isLoaded =
                (typeof google === "object" &&
                    typeof google.maps === "object" &&
                    !this.websiteEditService.callShared(
                        "googleMapsOption",
                        "shouldRefetchApiKey"
                    )) ||
                (await this.loadGoogleMaps(false));
            if (isLoaded) {
                this.canStart = await this.websiteEditService.callShared(
                    "googleMapsOption",
                    "initializeGoogleMaps",
                    [this.el, google.maps]
                );
            } else {
                this.websiteEditService.callShared(
                    "googleMapsOption",
                    "failedToInitializeGoogleMaps",
                    [this.el]
                );
            }
        }

        /**
         * Get the stored API key if any (or open a dialog to ask the user for one),
         * load and configure the Google Maps API.
         *
         * @param {boolean} [forceReconfigure=false]
         * @returns {Promise<void>}
         */
        async loadGoogleMaps(forceReconfigure = false) {
            /** @type {string | undefined} */
            const apiKey = await this.websiteMapService.getGMapAPIKey(true);
            const apiKeyValidation = await this.websiteMapService.validateGMapApiKey(apiKey);
            const shouldReconfigure = forceReconfigure || !apiKeyValidation.isValid;
            let didReconfigure = false;
            if (shouldReconfigure) {
                didReconfigure = await this.websiteEditService.callShared(
                    "googleMapsOption",
                    "configureGMapsAPI",
                    apiKey
                );
                if (!didReconfigure) {
                    this.websiteEditService.callShared("remove", "removeElement", this.el);
                }
            }
            if (!shouldReconfigure || didReconfigure) {
                const shouldRefetch = this.websiteEditService.callShared(
                    "googleMapsOption",
                    "shouldRefetchApiKey"
                );
                return !!(await this.loadGoogleMapsAPIFromService(shouldRefetch || didReconfigure));
            } else {
                return false;
            }
        }

        /**
         * Load the Google Maps API from the Google Map Service.
         * This method is set apart so it can be overridden for testing.
         *
         * @param {boolean} [shouldRefetch]
         * @returns {Promise<string|undefined>} A promise that resolves to an API
         *                                      key if found.
         */
        async loadGoogleMapsAPIFromService(shouldRefetch) {
            const apiKey = await this.websiteMapService.loadGMapAPI(true, shouldRefetch);
            this.websiteEditService.callShared("googleMapsOption", "shouldNotRefetchApiKey");
            return !!apiKey;
        }
    };

registry.category("public.interactions.edit").add("website.google_map", {
    Interaction: GoogleMap,
    mixin: GoogleMapEdit,
});
