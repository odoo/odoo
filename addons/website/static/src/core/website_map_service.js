/** @odoo-module native */
import { registry } from "@web/core/registry";
import { createGoogleMapsService } from "@website/utils/google_maps";

export const websiteMapService = {
    dependencies: ["public.interactions", "notification"],
    start(env, deps) {
        const publicInteractions = deps["public.interactions"];
        return createGoogleMapsService(deps.notification, () => {
            for (const el of document.querySelectorAll("section.s_google_map")) {
                publicInteractions.stopInteractions(el);
                publicInteractions.startInteractions(el);
            }
            promiseKeysResolves[lastKey]?.();
        }.bind(this);
        return {
            /**
             * @param {boolean} [refetch=false]
             */
            async getGMapAPIKey(refetch) {
                if (refetch || !gmapAPIKeyProm) {
                    gmapAPIKeyProm = (async () => {
                        try {
                            const data = await rpc("/website/google_maps_api_key");
                            return JSON.parse(data).google_maps_api_key || "";
                        } catch {
                            // Don't cache a failed fetch; allow a later retry.
                            gmapAPIKeyProm = null;
                            return "";
                        }
                    })();
                }
                return gmapAPIKeyProm;
            },
            /**
             * @param {boolean} [editableMode=false]
             * @param {boolean} [refetch=false]
             */
            async loadGMapAPI(editableMode, refetch) {
                // Note: only need refetch to reload a configured key and load the
                // library. If the library was loaded with a correct key and that the
                // key changes meanwhile... it will not work but we can agree the user
                // can bother to reload the page at that moment.
                // Check `gmapAPILoading` synchronously: `!(await gmapAPILoading)`
                // meant two concurrent first callers both awaited `undefined`
                // (falsy) and both entered the loader. Reset the cache when the
                // load fails so a later call still retries (the previous
                // await-false guard did).
                if (refetch || !gmapAPILoading) {
                    gmapAPILoading = (async () => {
                        try {
                            const key = await this.getGMapAPIKey(refetch);
                            lastKey = key;

                            if (key) {
                                if (!promiseKeys[key]) {
                                    promiseKeys[key] = new Promise((resolve) => {
                                        promiseKeysResolves[key] = resolve;
                                    });
                                    await loadJS(
                                        `https://maps.googleapis.com/maps/api/js?v=3.exp&libraries=places&callback=odoo_gmap_api_post_load&key=${encodeURIComponent(
                                            key,
                                        )}`,
                                    );
                                }
                                await promiseKeys[key];
                                // The resolver is only needed until the promise
                                // above settles; drop it so it doesn't stay
                                // referenced for the tab's whole lifetime.
                                delete promiseKeysResolves[key];
                                return key;
                            }
                            if (!editableMode && user.isAdmin) {
                                const message = _t("Cannot load google map.");
                                const urlTitle = _t("Check your configuration.");
                                notification.add(
                                    markup`<div>
                                        <span>${message}</span><br/>
                                        <a href="/odoo/action-website.action_website_configuration">${urlTitle}</a>
                                    </div>`,
                                    { type: "warning", sticky: true },
                                );
                            }
                            gmapAPILoading = null;
                            return false;
                        } catch {
                            gmapAPILoading = null;
                            return false;
                        }
                    })();
                }
                return gmapAPILoading;
            },
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
             * @see notifyGMapsError
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
                                      { error: await response.text() },
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
            },
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
                        key,
                    )}`,
                );
            },
        };
    },
};

registry.category("services").add("website_map", websiteMapService);
