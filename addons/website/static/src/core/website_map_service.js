import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { markup } from "@odoo/owl";

registry.category("services").add("website_map", {
    dependencies: ["public.interactions", "notification"],
    start(env, deps) {
        const publicInteractions = deps["public.interactions"];
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
             * @param {boolean} [editableMode=false]
             * @param {boolean} [refetch=false]
             */
            async loadGMapAPI(editableMode, refetch) {
                // Note: only need refetch to reload a configured key and load the
                // library. If the library was loaded with a correct key and that the
                // key changes meanwhile... it will not work but we can agree the user
                // can bother to reload the page at that moment.
                if (refetch || !gmapAPILoading) {
                    gmapAPILoading = new Promise(async resolve => {
                        const key = await this.getGMapAPIKey(refetch);

                        window.odoo_gmap_api_post_load = (async function odoo_gmap_api_post_load() {
                            for (const el of document.querySelectorAll("section.s_google_map")) {
                                publicInteractions.stopInteractions(el);
                                publicInteractions.startInteractions(el);
                            }
                            resolve(key);
                        }).bind(this);

                        if (!key) {
                            if (!editableMode && user.isAdmin) {
                                const message = _t("Cannot load google map.");
                                const urlTitle = _t("Check your configuration.");
                                notification.add(
                                    markup(`<div>
                                        <span>${message}</span><br/>
                                        <a href="/odoo/action-website.action_website_configuration">${urlTitle}</a>
                                    </div>`),
                                    { type: 'warning', sticky: true }
                                );
                            }
                            resolve(false);
                            gmapAPILoading = false;
                            return;
                        }
                        await loadJS(`https://maps.googleapis.com/maps/api/js?v=3.exp&libraries=places&callback=odoo_gmap_api_post_load&key=${encodeURIComponent(key)}`);
                    });
                }
                return gmapAPILoading;
            },
        }
    }
});
