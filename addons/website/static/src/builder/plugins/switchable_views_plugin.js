import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class SwitchableViewsPlugin extends Plugin {
    static id = "switchableViews";
    static dependencies = ["customizeWebsite"];
    static shared = /** @type {const} */ (["getSwitchableRelatedViews"]);

    /**
     * @returns {Promise<[]>}
     */
    getSwitchableRelatedViews() {
        if (!this.prom) {
            const viewKey = this.document.querySelector("html").dataset.viewXmlid;
            if (this.services.website.isDesigner && viewKey) {
                this.prom = rpc("/website/get_switchable_related_views", {
                    key: viewKey,
                });
                this.prom.then((views) => {
                    for (const view of views) {
                        const promise = Promise.resolve(view.active);
                        this.dependencies.customizeWebsite.populateCache(view.key, promise);
                    }
                });
            } else {
                this.prom = Promise.resolve([]);
            }
        }
        return this.prom;
    }
}

registry.category("website-plugins").add(SwitchableViewsPlugin.id, SwitchableViewsPlugin);
