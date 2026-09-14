/** @odoo-module native */
// @ts-check
import { markup } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { makeLogger } from "@web/core/debug/debug_logger";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { user } from "@web/core/user";
import { uniqueId } from "@web/core/utils/functions";

const log = makeLogger("website.service.map");

/**
 * Keep each runtime's API cache local while sharing retry and readiness rules.
 * @param {{ add: Function }} notification
 * @param {() => void} [onReady]
 */
export function createGoogleMapsService(notification, onReady = () => {}) {
    let gmapAPIKeyProm;
    let gmapAPILoading;
    const apiLoads = new Map();

    function loadAPI(key) {
        if (!apiLoads.has(key)) {
            // A refetch can overlap an older script: readiness belongs to
            // the script's callback, never to the last requested key.
            const callbackName = uniqueId("odoo_gmap_api_post_load_");
            const ready = new Promise((resolve) => {
                window[callbackName] = () => {
                    log.pipeline("gmap api ready", () => ({ callbackName }));
                    resolve(undefined);
                    onReady();
                };
            });
            const endLoad = log.perf("loadGMapAPI script and readiness", () => ({
                callbackName,
            }));
            const loading = Promise.resolve().then(async () => {
                try {
                    await loadJS(
                        `https://maps.googleapis.com/maps/api/js?v=3.exp&libraries=places&callback=${callbackName}&key=${encodeURIComponent(key)}`,
                    );
                    await ready;
                    return key;
                } catch (error) {
                    apiLoads.delete(key);
                    throw error;
                } finally {
                    delete window[callbackName];
                    endLoad();
                }
            });
            apiLoads.set(key, loading);
        }
        return apiLoads.get(key);
    }
    return {
        /**
         * @param {boolean} [refetch=false]
         */
        async getGMapAPIKey(refetch) {
            log.logic("getGMapAPIKey", () => ({
                refetch,
                cached: !!gmapAPIKeyProm,
            }));
            if (refetch || !gmapAPIKeyProm) {
                const request = Promise.resolve().then(async () => {
                    const endKey = log.perf("getGMapAPIKey rpc");
                    try {
                        const data = await rpc("/website/google_maps_api_key");
                        return JSON.parse(data).google_maps_api_key || "";
                    } catch {
                        log.logic("getGMapAPIKey: rpc or parse failed, cache reset");
                        if (gmapAPIKeyProm === request) {
                            gmapAPIKeyProm = null;
                        }
                        return "";
                    } finally {
                        endKey();
                    }
                });
                gmapAPIKeyProm = request;
            }
            return gmapAPIKeyProm;
        },
        /**
         * @param {boolean} [editableMode=false]
         * @param {boolean} [refetch=false]
         */
        async loadGMapAPI(editableMode, refetch) {
            log.logic("loadGMapAPI", () => ({
                editableMode,
                refetch,
                loading: !!gmapAPILoading,
            }));
            if (refetch || !gmapAPILoading) {
                const loading = Promise.resolve().then(async () => {
                    try {
                        const key = await this.getGMapAPIKey(refetch);
                        if (key) {
                            return await loadAPI(key);
                        }
                        log.logic("loadGMapAPI: no API key", () => ({
                            editableMode,
                            notifyAdmin: !editableMode && user.isAdmin,
                        }));
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
                        if (gmapAPILoading === loading) {
                            gmapAPILoading = null;
                        }
                        return false;
                    } catch {
                        log.logic("loadGMapAPI: loading failed, cache reset");
                        if (gmapAPILoading === loading) {
                            gmapAPILoading = null;
                        }
                        return false;
                    }
                });
                gmapAPILoading = loading;
            }
            return gmapAPILoading;
        },
        /**
         * @param {string} key
         * @returns {Promise<{ isValid: boolean, message?: string }>}
         */
        async validateGMapApiKey(key) {
            if (key) {
                try {
                    const endValidate = log.perf("validateGMapApiKey fetch");
                    const response = await this.fetchGoogleMap(key);
                    const isValid = response.status === 200;
                    endValidate({ status: response.status, isValid });
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
                    log.logic("validateGMapApiKey: fetch failed");
                    return {
                        isValid: false,
                        message: _t("Check your connection and try again"),
                    };
                }
            } else {
                log.logic("validateGMapApiKey: empty key");
                return { isValid: false };
            }
        },
        /**
         * @param {string} key
         * @returns {Promise<Response>}
         */
        async fetchGoogleMap(key) {
            return await fetch(
                `https://maps.googleapis.com/maps/api/staticmap?center=belgium&size=10x10&key=${encodeURIComponent(
                    key,
                )}`,
            );
        },
    };
}
