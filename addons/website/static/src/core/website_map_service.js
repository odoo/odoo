import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { markup } from "@odoo/owl";

export const websiteMapService = {
    dependencies: ["public.interactions", "notification"],
    start(env, deps) {
        const publicInteractions = deps["public.interactions"];
        const notification = deps["notification"];
        let gmapAPIKeyProm;
        let gmapAPILoading;
        const promiseKeys = {};
        const promiseKeysResolves = {};
        let lastKey;
        return {
            /**
             * @param {boolean} [refetch=false]
             */
            async getGMapAPIKey(refetch) {
                if (refetch || !gmapAPIKeyProm) {
                    gmapAPIKeyProm = (async () => {
                        const data = await rpc("/website/google_maps_api_key");
                        return JSON.parse(data).google_maps_api_key || "";
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
                if (refetch || !(await gmapAPILoading)) {
                    gmapAPILoading = (async () => {
                        const key = await this.getGMapAPIKey(refetch);
                        lastKey = key;

                        if (key) {
                            if (!promiseKeys[key]) {
                                promiseKeys[key] = new Promise((resolve) => {
                                    promiseKeysResolves[key] = resolve;
                                });
                                ((g) => {
                                    var h,
                                        a,
                                        k,
                                        p = "The Google Maps JavaScript API",
                                        c = "google",
                                        l = "importLibrary",
                                        q = "__ib__",
                                        m = document,
                                        b = window;
                                    b = b[c] || (b[c] = {});
                                    var d = b.maps || (b.maps = {}),
                                        r = new Set(),
                                        e = new URLSearchParams(),
                                        u = () =>
                                            h ||
                                            // eslint-disable-next-line no-async-promise-executor
                                            (h = new Promise(async (f, n) => {
                                                await (a = m.createElement("script"));
                                                e.set("libraries", [...r] + "");
                                                for (k in g) {
                                                    e.set(
                                                        k.replace(
                                                            /[A-Z]/g,
                                                            (t) => "_" + t[0].toLowerCase()
                                                        ),
                                                        g[k]
                                                    );
                                                }
                                                e.set("callback", c + ".maps." + q);
                                                a.src =
                                                    `https://maps.${c}apis.com/maps/api/js?` + e;
                                                d[q] = f;
                                                a.onerror = () =>
                                                    (h = n(Error(p + " could not load.")));
                                                var script = m.querySelector("script[nonce]");
                                                a.nonce = script ? script.nonce : "";
                                                m.head.append(a);
                                            }));
                                    d[l]
                                        ? console.warn(p + " only loads once. Ignoring:", g)
                                        : (d[l] = (f, ...n) =>
                                              r.add(f) && u().then(() => d[l](f, ...n)));
                                })({
                                    key: key,
                                    v: "weekly",
                                });
                                for (const el of document.querySelectorAll(
                                    "section.s_google_map"
                                )) {
                                    publicInteractions.stopInteractions(el);
                                    publicInteractions.startInteractions(el);
                                }
                                promiseKeysResolves[lastKey]?.();
                            }
                            await promiseKeys[key];
                            return key;
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
            async fetchGoogleMap(key) {
                return await fetch(
                    `https://maps.googleapis.com/maps/api/staticmap?center=belgium&size=10x10&key=${encodeURIComponent(
                        key
                    )}`
                );
            },
        };
    },
};

registry.category("services").add("website_map", websiteMapService);
