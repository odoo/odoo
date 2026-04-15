import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { Plugin } from "@html_editor/plugin";
import { GoogleMapsApiKeyDialog } from "./google_maps_api_key_dialog";
import { GoogleMapsOption } from "./google_maps_option";
import { Deferred } from "@web/core/utils/concurrency";
import { BuilderAction } from "@html_builder/core/builder_action";

/**
 * A `google.maps.places.PlaceResult` object.
 * Here listed are only the few properties used here. For a full list, see:
 * {@link https://developers.google.com/maps/documentation/javascript/reference/places-service#PlaceResult}
 *
 * @typedef {Object} Place
 * @property {string} [formatted_address]
 * @property {Object} [geometry]
 * @property {Object} [geometry.location]
 * @property {function():number} geometry.location.lat
 * @property {function():number} geometry.location.lng
 */
/**
 * A string defining GPS coordinates in the form "`Latitude`,`Longitude`".
 * @typedef {`${number},${number}`} Coordinates
 */
/**
 * @typedef {{ isValid: boolean, message?: string }} ApiKeyValidation
 */

/**
 * @typedef { Object } GoogleMapsOptionShared
 * @property { GoogleMapsOptionPlugin['configureGMapsAPI'] } configureGMapsAPI
 * @property { GoogleMapsOptionPlugin['initializeGoogleMaps'] } initializeGoogleMaps
 * @property { GoogleMapsOptionPlugin['failedToInitializeGoogleMaps'] } failedToInitializeGoogleMaps
 * @property { GoogleMapsOptionPlugin['shouldRefetchApiKey'] } shouldRefetchApiKey
 * @property { GoogleMapsOptionPlugin['shouldNotRefetchApiKey'] } shouldNotRefetchApiKey
 * @property { GoogleMapsOptionPlugin['commitPlace'] } commitPlace
 * @property { GoogleMapsOptionPlugin['getPlace'] } getPlace
 * @property { GoogleMapsOptionPlugin['getMapsAPI'] } getMapsAPI
 * @property { GoogleMapsOptionPlugin['notifyGMapsError'] } notifyGMapsError
 */

export class GoogleMapsOptionPlugin extends Plugin {
    static id = "googleMapsOption";
    static dependencies = ["history", "edit_interaction"];
    static shared = [
        "configureGMapsAPI",
        "initializeGoogleMaps",
        "failedToInitializeGoogleMaps",
        "shouldRefetchApiKey",
        "shouldNotRefetchApiKey",
        "commitPlace",
        "getPlace",
        "getMapsAPI",
        "notifyGMapsError",
    ];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [GoogleMapsOption],
        so_content_addition_selector: [".s_google_map"],
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        builder_actions: {
            ResetMapColorAction,
            ShowDescriptionAction,
        },
        // TODO remove when the snippet will have a "Height" option.
        keep_overlay_options: (el) => el.matches(".s_google_map"),
    };

    setup() {
        this.websiteService = this.services.website;
        this.dialog = this.services.dialog;
        this.orm = this.services.orm;
        this.notification = this.services.notification;

        /** @type {Map<Coordinates, Place>} */
        this.gpsMapCache = new Map();

        /** @type {Map<HTMLElement, Deferred} */
        this.recentlyDroppedSnippetDeferredInit = new Map();
    }

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_google_map")) {
            const deferredInit = new Deferred();
            this.recentlyDroppedSnippetDeferredInit.set(snippetEl, deferredInit);
            this.dependencies.edit_interaction.restartInteractions(snippetEl);
            const initSuccess = await deferredInit;
            this.recentlyDroppedSnippetDeferredInit.delete(snippetEl);
            if (!initSuccess) {
                return true; // cancel
            }
        }
    }

    failedToInitializeGoogleMaps(editingElement) {
        this.recentlyDroppedSnippetDeferredInit.get(editingElement)?.resolve(false);
    }

    getMapsAPI() {
        return this.mapsAPI;
    }

    async initializeGoogleMaps(editingElement, mapsAPI) {
        this.recentlyDroppedSnippetDeferredInit.get(editingElement)?.resolve(true);
        if (mapsAPI) {
            await mapsAPI.importLibrary("places");
            this.mapsAPI = mapsAPI;
            this.placesAPI = mapsAPI.places;
        }
        // Try to fail early if there is a configuration issue.
        return (
            !!this.placesAPI &&
            !!(await this.getPlace(editingElement, editingElement.dataset.mapGps))
        );
    }

    /**
     * Take a set of coordinates and perform a search on them to return a
     * place's formatted address.
     *
     * @param {Element} editingElement
     * @param {Coordinates} coordinates
     * @returns {Promise<Place | undefined>}
     */
    async getPlace(editingElement, coordinates) {
        const place = await this.nearbySearch(coordinates, editingElement);
        if (!place && !this.isGoogleMapsErrorBeingHandled) {
            // No place found at these cordinates (empty result).
            this.undoInitialize?.();
        } else {
            return place;
        }
    }

    /**
     * Commit a place's coordinates and address to the cache and to the editing
     * element's dataset, then re-render the map to reflect it.
     *
     * @param {Element} editingElement
     * @param {Place} place
     */
    commitPlace(editingElement, place) {
        if (place?.geometry) {
            const location = place.geometry.location;
            /** @type {Coordinates} */
            const coordinates = `(${location.lat},${location.lng})`;
            this.gpsMapCache.set(coordinates, place);
            /** @type {{mapGps: Coordinates, pinAddress: string}} */
            const currentMapData = editingElement.dataset;
            const { mapGps, pinAddress } = currentMapData;
            if (mapGps !== coordinates || pinAddress !== place.formatted_address) {
                editingElement.dataset.mapGps = coordinates;
                editingElement.dataset.pinAddress = place.formatted_address;
                // Restart interactions to re-render the map.
                this.dispatchTo("content_manually_updated_handlers", editingElement);
                this.dependencies.history.addStep();
            }
        }
    }

    /**
     * Test the validity of the API key provided if any. If none was provided,
     * or the key was invalid, or the `force` argument is `true`, open the API
     * key dialog to prompt the user to provide a new API key.
     *
     * @param {Object} param
     * @param {string} [param.apiKey]
     * @returns {Promise<boolean>} true if a new API key was written to db.
     */
    async configureGMapsAPI(apiKey) {
        this.undoInitialize = this.dependencies.history.makeSavePoint();
        /** @type {number} */
        const websiteId = this.websiteService.currentWebsite.id;

        /** @type {boolean} */
        const didReconfigure = await new Promise((resolve) => {
            let isInvalidated = false;
            // Open the Google API Key Dialog.
            this.dialog.add(
                GoogleMapsApiKeyDialog,
                {
                    originalApiKey: apiKey,
                    onSave: async (newApiKey) => {
                        await this.orm.write("website", [websiteId], {
                            google_maps_api_key: newApiKey,
                        });
                        this.shouldRefetchApiKey = false;
                        isInvalidated = true;
                    },
                },
                {
                    onClose: () => resolve(isInvalidated),
                }
            );
        });
        return didReconfigure;
    }

    /**
     * @param {Coordinates} coordinates
     * @param {HTMLElement} editingElement
     * @returns {Promise<Place|undefined>}
     */
    async nearbySearch(coordinates, editingElement) {
        const place = this.gpsMapCache.get(coordinates);
        if (place) {
            return place;
        }

        const p = coordinates.substring(1).slice(0, -1).split(",");
        try {
            const { places } = await this.placesAPI.Place.searchNearby({
                // Use 'searchNearby' to avoid relying on the GMaps Geocoder,
                // which the user may not have enabled... but ideally Geocoder
                // should be used to get the exact location at those coordinates
                // and to limit billing query count.
                fields: ["id", "location", "formattedAddress"],
                locationRestriction: {
                    center: { lat: Number(p[0]), lng: Number(p[1]) },
                    radius: 10,
                },
                maxResultCount: 1,
            });
            if (!places.length) {
                return;
            }
            const placeResult = places[0];
            const place = {
                place_id: placeResult.id,
                formatted_address: placeResult.formattedAddress,
                geometry: {
                    location: {
                        lat: placeResult.location.lat(),
                        lng: placeResult.location.lng(),
                    },
                },
            };
            this.gpsMapCache.set(coordinates, place);
            return place;
        } catch (error) {
            console.error(error);
            this.notifyGMapsError(editingElement);
            return;
        }
    }

    /**
     * Indicates to the user there is an error with the google map API and
     * re-opens the configuration dialog. For good measure, this also removes
     * the related snippet entirely as this is what is done in case of critical
     * error.
     */
    notifyGMapsError(editingElement) {
        // TODO this should be better to detect all errors. This is random.
        // When misconfigured (wrong APIs enabled), sometimes Google throws
        // errors immediately (which then reaches this code), sometimes it
        // throws them later (which then induces an error log in the console
        // and random behaviors).
        if (!this.isGoogleMapsErrorBeingHandled) {
            this.isGoogleMapsErrorBeingHandled = true;

            this.notification.add(
                _t(
                    "A Google Maps error occurred. Make sure to read the key configuration popup carefully."
                ),
                { type: "danger", sticky: true }
            );
            // Try again: invalidate the API key then restart interactions.
            this.orm
                .write("website", [this.websiteService.currentWebsite.id], {
                    google_maps_api_key: "",
                })
                .then(() => {
                    this.wasApiKeyInvalidated = true;
                    this.isGoogleMapsErrorBeingHandled = false;
                    this.dependencies.edit_interaction.restartInteractions(editingElement);
                });
        }
    }
    shouldRefetchApiKey() {
        return this.wasApiKeyInvalidated || false;
    }
    shouldNotRefetchApiKey() {
        this.wasApiKeyInvalidated = false;
    }
}

export class ResetMapColorAction extends BuilderAction {
    static id = "resetMapColor";
    apply({ editingElement }) {
        editingElement.dataset.mapColor = "";
    }
}
export class ShowDescriptionAction extends BuilderAction {
    static id = "showDescription";
    isApplied({ editingElement }) {
        return !!editingElement.querySelector(".description");
    }
    apply({ editingElement }) {
        editingElement.append(renderToElement("html_builder.GoogleMapsDescription"));
    }
    clean({ editingElement }) {
        editingElement.querySelector(".description").remove();
    }
}

registry.category("website-plugins").add(GoogleMapsOptionPlugin.id, GoogleMapsOptionPlugin);
