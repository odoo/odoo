/* eslint-disable prettier/prettier */
/* eslint-disable no-async-promise-executor */

import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { markup } from "@odoo/owl";
import { escape } from "@web/core/utils/strings";

registry.category("services").add("google_maps", {
    dependencies: [ "notification" ],
    start(env, deps) {
        const notification = deps["notification"];
        let gMapsAPIKeyProm;
        let gMapsAPILoading;
        const promiseKeys = {};
        const promiseKeysResolves = {};
        let lastKey;
        window.odoo_gmaps_api_post_load = (async function odoo_gmaps_api_post_load() {
            promiseKeysResolves[lastKey]?.();
        }).bind(this);
        return {
            /**
             * @param {boolean} [refetch=false]
             */
            async getGMapsAPIKey(refetch) {
                if (refetch || !gMapsAPIKeyProm) {
                    gMapsAPIKeyProm = new Promise(async resolve => {
                        const data = await rpc('/website/google_maps_api_key');
                        resolve(JSON.parse(data).google_maps_api_key || '');
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
                    gMapsAPILoading = new Promise(async resolve => {
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
                                    markup(`<div>
                                        <span>${escape(message)}</span><br/>
                                        <a href="/odoo/action-website.action_website_configuration">${escape(urlTitle)}</a>
                                    </div>`),
                                    { type: 'warning', sticky: true }
                                );
                            }
                            resolve(false);
                        }
                    });
                }
                return gMapsAPILoading;
            },
        };
    },
});
