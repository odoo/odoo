import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { SwitchableViews } from "./switchable_views";

/**
 * @typedef { Object } SwitchableViewsShared
 * @property { SwitchableViewsPlugin['getSwitchableRelatedViews'] } getSwitchableRelatedViews
 */

export class SwitchableViewsPlugin extends Plugin {
    static id = "switchableViews";
    static dependencies = ["customizeWebsite"];
    static shared = ["getSwitchableRelatedViews"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [SwitchableViews],
    };

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
