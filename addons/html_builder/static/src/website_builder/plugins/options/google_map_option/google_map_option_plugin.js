/* global google */

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";
import { Plugin } from "@html_editor/plugin";
import { GoogleMapApiKeyDialog } from "./google_map_api_key_dialog";
import { GoogleMapOption } from "./google_map_option";

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

export class GoogleMapOptionPlugin extends Plugin {
    static id = "googleMapOption";
    static dependencies = ["history", "remove"];
    resources = {
        builder_options: [
            {
                OptionComponent: GoogleMapOption,
                selector: ".s_google_map",
                props: {
                    getPlace: this.getPlace.bind(this),
                    onPlaceChanged: this.commitPlace.bind(this),
                },
            },
        ],
        builder_actions: this.getActions(),
        normalize_handlers: async (root) => {
            for (const snippet of root.querySelectorAll(".s_google_map")) {
                if (!this.isGoogleMapsReady && !this.isGoogleMapsErrorBeingHandled) {
                    await this.loadGoogleMaps(snippet);
                } else if (!this.mapsAPI) {
                    this.mapsAPI = google.maps;
                    this.placesAPI = google.maps.places;
                }
            }
        },
        restore_savepoint_handlers: () => {
            // Restart interactions to re-render the map.
            this.dispatchTo("content_manually_updated_handlers");
        },
    };

    setup() {
        this.websiteService = this.services.website;
        // @TODO mysterious-egg: the `google_map service` is a duplicate of the
        // `website_map_service`, but without the dependency on public
        // interactions. These are used only to restart the interactions once
        // the API is loaded. We do this in the plugin instead. Once
        // `html_builder` replaces `website`, we should be able to remove
        // `website_map_service` since only google_map service will be used.
        this.googleMapService = this.services.google_map;
        this.dialog = this.services.dialog;
        this.orm = this.services.orm;
        this.notification = this.services.notification;

        /** @type {Map<Coordinates, Place>} */
        this.gpsMapCache = new Map();
    }

    getActions() {
        return {
            resetMapColor: {
                apply: ({ editingElement }) => {
                    editingElement.dataset.mapColor = "";
                },
            },
            showDescription: {
                isApplied: ({ editingElement }) => !!editingElement.querySelector(".description"),
                apply: ({ editingElement }) => {
                    editingElement.append(renderToElement("html_builder.GoogleMapDescription"));
                },
                clean: ({ editingElement }) => {
                    editingElement.querySelector(".description").remove();
                },
            },
        };
    }

    /**
     * Get the stored API key if any (or open a dialog to ask the user for one),
     * load and configure the Google Maps API.
     *
     * @param {Element} editingElement
     * @param {boolean} [forceReconfigure=false]
     * @returns {Promise<void>}
     */
    async loadGoogleMaps(editingElement, forceReconfigure = false) {
        /** @type {string | undefined} */
        const apiKey = await this.googleMapService.getGMapAPIKey();
        const didReconfigure = await this.configureGMapAPI({ apiKey, force: forceReconfigure });
        const didLoad = !!(await this.loadGoogleMapAPIFromService(didReconfigure));
        if (didLoad) {
            this.mapsAPI = google.maps;
            this.placesAPI = google.maps.places;
        }
        // Try to fail early if there is a configuration issue.
        const foundPlace = !!(await this.getPlace(editingElement, editingElement.dataset.mapGps));
        this.isGoogleMapsReady = didLoad && foundPlace;
        // @TODO mysterious-egg: this would not be needed if we didn't duplicate
        // the API loading:
        if (didReconfigure) {
            // Make sure to reload the API in the iframe with the new API key.
            window.top.refetchGoogleMaps = true;
            // Restart interactions to re-render the map.
            this.dispatchTo("content_manually_updated_handlers");
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
    async loadGoogleMapAPIFromService(shouldRefetch) {
        return this.googleMapService.loadGMapAPI(true, shouldRefetch);
    }

    /**
     * Take a set of coordinates and perform a search on them to return a
     * place's formatted address. If it failed, there must be an issue with the
     * API so remove the snippet.
     *
     * @param {Element} editingElement
     * @param {Coordinates} coordinates
     * @returns {Promise<Place | undefined>}
     */
    async getPlace(editingElement, coordinates) {
        const place = await this.nearbySearch(editingElement, coordinates);
        if (!place && !this.isGoogleMapsErrorBeingHandled) {
            // Somehow the search failed but Google didn't trigger an error.
            // @TODO mysterious-egg should we keep this? Seems radical.
            this.dependencies.remove.removeElement(editingElement);
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
            const coordinates = `(${location.lat()},${location.lng()})`;
            this.gpsMapCache.set(coordinates, place);
            /** @type {{mapGps: Coordinates, pinAddress: string}} */
            const currentMapData = editingElement.dataset;
            const { mapGps, pinAddress } = currentMapData;
            if (mapGps !== coordinates || pinAddress !== place.formatted_address) {
                editingElement.dataset.mapGps = coordinates;
                editingElement.dataset.pinAddress = place.formatted_address;
                // Restart interactions to re-render the map.
                this.dispatchTo("content_manually_updated_handlers");
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
     * @param {boolean} [param.force] set to true to open the API Key dialog
     *                                even if the provided API key is valid.
     * @returns {Promise<boolean>} true if a new API key was written to db.
     */
    async configureGMapAPI({ apiKey, force }) {
        const apiKeyValidation = await this.validateGMapApiKey(apiKey);
        if (!force && apiKeyValidation.isValid) {
            return false;
        }
        /** @type {number} */
        const websiteId = this.websiteService.currentWebsite.id;

        /** @type {boolean} */
        const didReconfigure = await new Promise((resolve) => {
            let isInvalidated = false;
            // Open the Google API Key Dialog.
            this.dialog.add(
                GoogleMapApiKeyDialog,
                {
                    originalApiKey: apiKey,
                    originalApiKeyValidation: apiKeyValidation,
                    onSave: async (newApiKey) => {
                        await this.orm.write("website", [websiteId], {
                            google_maps_api_key: newApiKey,
                        });
                        isInvalidated = true;
                    },
                    validateGMapApiKey: this.validateGMapApiKey.bind(this),
                },
                {
                    onClose: () => resolve(isInvalidated),
                }
            );
        });
        return didReconfigure;
    }

    /**
     * Send a request to the Google Maps API, using the given API key, so as to
     * get a response which can be used to test the validity of said key.
     * This method is set apart so it can be overridden for testing.
     *
     * @param {string} key
     * @returns {Promise<{ status: number }>}
     */
    async fetchGoogleMap(key) {
        return await fetch(
            `https://maps.googleapis.com/maps/api/staticmap?center=belgium&size=10x10&key=${encodeURIComponent(
                key
            )}`
        );
    }

    /**
     * Send a request to the Google Maps API to test the validity of the given
     * API key. Return an object with the error message if any, and a boolean
     * that is true if the response from the API had a status of 200.
     *
     * Note: The response will be 200 so long as the API key has billing, Static
     * API and Javascript API enabled. However, for our purposes, we also need
     * the Places API enabled. To deal with that case, we perform a nearby
     * search immediately after validation. If it fails, the error is handled
     * and the dialog is re-opened.
     * @see nearbySearch
     * @see notifyGMapError
     *
     * @param {string} key
     * @returns {Promise<ApiKeyValidation>}
     */
    async validateGMapApiKey(key) {
        if (key) {
            try {
                const response = await this.fetchGoogleMap(key);
                const isValid = response.status === 200;
                return {
                    isValid,
                    message: isValid
                        ? undefined
                        : _t(
                              "Invalid API Key. The following error was returned by Google: %(error)s",
                              { error: await response.text() }
                          ),
                };
            } catch {
                return {
                    isValid: false,
                    message: _t("Check your connection and try again"),
                };
            }
        } else {
            return { isValid: false };
        }
    }

    /**
     * @param {Element} editingElement
     * @param {Coordinates} coordinates
     * @param {boolean} [notify=true]
     * @returns {Promise<Place|undefined>}
     */
    async nearbySearch(editingElement, coordinates, notify = true) {
        const place = this.gpsMapCache.get(coordinates);
        if (place) {
            return place;
        }

        const p = coordinates.substring(1).slice(0, -1).split(",");
        const location = new this.mapsAPI.LatLng(p[0] || 0, p[1] || 0);
        return new Promise((resolve) => {
            const placesService = new this.placesAPI.PlacesService(document.createElement("div"));
            placesService.nearbySearch(
                {
                    // Do a 'nearbySearch' followed by 'getDetails' to avoid using
                    // GMap Geocoder which the user may not have enabled... but
                    // ideally Geocoder should be used to get the exact location at
                    // those coordinates and to limit billing query count.
                    location,
                    radius: 1,
                },
                (results, status) => {
                    const GMAP_CRITICAL_ERRORS = [
                        this.placesAPI.PlacesServiceStatus.REQUEST_DENIED,
                        this.placesAPI.PlacesServiceStatus.UNKNOWN_ERROR,
                    ];
                    if (status === this.placesAPI.PlacesServiceStatus.OK) {
                        placesService.getDetails(
                            {
                                placeId: results[0].place_id,
                                fields: ["geometry", "formatted_address"],
                            },
                            (place, status) => {
                                if (status === this.placesAPI.PlacesServiceStatus.OK) {
                                    this.gpsMapCache.set(coordinates, place);
                                    resolve(place);
                                } else if (GMAP_CRITICAL_ERRORS.includes(status)) {
                                    if (notify) {
                                        this.notifyGMapError(editingElement);
                                    }
                                    resolve();
                                }
                            }
                        );
                    } else if (GMAP_CRITICAL_ERRORS.includes(status)) {
                        if (notify) {
                            this.notifyGMapError(editingElement);
                        }
                        resolve();
                    } else {
                        resolve();
                    }
                }
            );
        });
    }

    /**
     * Indicates to the user there is an error with the google map API and
     * re-opens the configuration dialog. For good measure, this also removes
     * the related snippet entirely as this is what is done in case of critical
     * error.
     *
     * @param {Element} editingElement
     */
    notifyGMapError(editingElement) {
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
            // Try again.
            this.loadGoogleMaps(editingElement, true).then(() => {
                this.isGoogleMapsErrorBeingHandled = false;
            });

            // @TODO mysterious-egg: should we still do this, which was just
            // done as a result of reporting a critical error?
            setTimeout(() => this.dependencies.remove.removeElement(editingElement));
        }
    }
}

registry.category("website-plugins").add(GoogleMapOptionPlugin.id, GoogleMapOptionPlugin);
