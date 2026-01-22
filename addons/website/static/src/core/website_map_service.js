import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { markup } from "@odoo/owl";
import { escape } from "@web/core/utils/strings";

registry.category("services").add("website_map", {
    dependencies: ["public.interactions", "notification"],
    start(env, deps) {
        const notification = deps["notification"];
        let gmapAPIKeyProm;
        let gmapAPILoading;
        return {
            /**
             * @param {boolean} [refetch=false]
             */
            async getGMapAPIKey(refetch) {
                if (refetch || !gmapAPIKeyProm) {
                    gmapAPIKeyProm = new Promise(async resolve => {
                        const data = await rpc('/website/google_maps_api_key');
                        resolve(JSON.parse(data).google_maps_api_key || '');
                    });
                }
                return gmapAPIKeyProm;
            },
            /**
             * Initializes the Google Maps JavaScript API using the dynamic library
             * import bootstrap pattern. Libraries (e.g. "maps", "places", "marker") are
             * loaded lazily via `google.maps.importLibrary()` at each call site.
             *
             * @private
             * @param {string} key - The Google Maps API key
             * @see https://developers.google.com/maps/documentation/javascript/load-maps-js-api#dynamic-library-import
             */
            initGoogleMapsAPI(key) {
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
                            (h = new Promise(async (f, n) => {
                                await (a = m.createElement("script"));
                                e.set("libraries", [...r] + "");
                                for (k in g) {
                                    e.set(
                                        k.replace(/[A-Z]/g, (t) => "_" + t[0].toLowerCase()),
                                        g[k]
                                    );
                                }
                                e.set("callback", c + ".maps." + q);
                                a.src = `https://maps.${c}apis.com/maps/api/js?` + e;
                                d[q] = f;
                                a.onerror = () => (h = n(Error(p + " could not load.")));
                                a.nonce = m.querySelector("script[nonce]")?.nonce || "";
                                m.head.append(a);
                            }));
                    d[l]
                        ? console.warn(p + " only loads once. Ignoring:", g)
                        : (d[l] = (f, ...n) => r.add(f) && u().then(() => d[l](f, ...n)));
                })({
                    key: key,
                    v: "weekly",
                });
            },
            /**
             * @param {boolean} [editableMode=false]
             * @param {boolean} [refetch=false]
             */
            async loadGMapAPI(editableMode, refetch) {
                // Note: only need refetch to reload a configured key and load the
                // library. If the library was loaded with a correct key and that the
                // key changes meanwhile... it will not work but we can agree the user
                // can bother to reload the page when they are notified.
                if (refetch || !gmapAPILoading) {
                    gmapAPILoading = new Promise(async resolve => {
                        const key = await this.getGMapAPIKey(refetch);

                        if (!key) {
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
                            gmapAPILoading = false;
                            return;
                        }
                        this.initGoogleMapsAPI(key);
                        resolve(key);
                    });
                }
                return gmapAPILoading;
            },
        }
    }
});
