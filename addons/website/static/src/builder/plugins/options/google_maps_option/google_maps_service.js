/* eslint-disable no-async-promise-executor */

import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { markup } from "@odoo/owl";

registry.category("services").add("google_maps", {
    dependencies: ["notification"],
    start(env, deps) {
        const notification = deps["notification"];
        let gMapsAPIKeyProm;
        let gMapsAPILoading;
        const promiseKeys = {};
        const promiseKeysResolves = {};
        let lastKey;
        window.odoo_gmaps_api_post_load = async function odoo_gmaps_api_post_load() {
            promiseKeysResolves[lastKey]?.();
        }.bind(this);
        return {
            /**
             * @param {boolean} [refetch=false]
             */
            async getGMapsAPIKey(refetch) {
                if (refetch || !gMapsAPIKeyProm) {
                    gMapsAPIKeyProm = new Promise(async (resolve) => {
                        const data = await rpc("/website/google_maps_api_key");
                        resolve(JSON.parse(data).google_maps_api_key || "");
                    });
                }
                return gMapsAPIKeyProm;
            },
            /**
             * @param {boolean} [editableMode=false]
             * @param {boolean} [refetch=false]
             */
            async loadGMapsAPI(editableMode, refetch) {
                // Note: only need refetch to reload a configured key and load
                // the library. If the library was loaded with a correct key and
                // that the key changes meanwhile... it will not work but we can
                // agree the user can bother to reload the page at that moment.
                if (refetch || !gMapsAPILoading) {
                    gMapsAPILoading = new Promise(async (resolve) => {
                        const key = await this.getGMapsAPIKey(refetch);
                        lastKey = key;

                        if (key) {
                            if (!promiseKeys[key]) {
                                promiseKeys[key] = new Promise((resolve) => {
                                    promiseKeysResolves[key] = resolve;
                                });
                                await loadJS(
                                    `https://maps.googleapis.com/maps/api/js?v=3.exp&libraries=places&callback=odoo_gmaps_api_post_load&key=${encodeURIComponent(
                                        key
                                    )}`
                                );
                            }
                            await promiseKeys[key];
                            resolve(key);
                        } else {
                            if (!editableMode && user.isAdmin) {
                                const message = _t("Cannot load google map.");
                                const urlTitle = _t("Check your configuration.");
                                notification.add(
                                    markup`<div>
                                        <span>${message}</span><br/>
                                        <a href="/odoo/action-website.action_website_configuration">${urlTitle}</a>
                                    </div>`,
                                    { type: "warning", sticky: true }
                                );
                            }
                            resolve(false);
                        }
                    });
                }
                return gMapsAPILoading;
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
            async validateGMapsApiKey(key) {
                if (key) {
                    try {
                        const response = await this.fetchGoogleMaps(key);
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
            },
            /**
             * Send a request to the Google Maps API, using the given API key, so as to
             * get a response which can be used to test the validity of said key.
             * This method is set apart so it can be overridden for testing.
             *
             * @param {string} key
             * @returns {Promise<{ status: number }>}
             */
            async fetchGoogleMaps(key) {
                return await fetch(
                    `https://maps.googleapis.com/maps/api/staticmap?center=belgium&size=10x10&key=${encodeURIComponent(
                        key
                    )}`
                );
            },
        };
    },
});
