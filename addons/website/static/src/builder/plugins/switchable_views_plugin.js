import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { SwitchableViews } from "./switchable_views";

export class SwitchableViewsPlugin extends Plugin {
    static id = "switchableViews";
    static dependencies = ["customizeWebsite"];

    resources = {
        builder_options: {
            OptionComponent: SwitchableViews,
            selector: ".o_portal_wrap",
            props: {
                getSwitchableRelatedViews: this.getSwitchableRelatedViews.bind(this),
            },
            groups: ["website.group_website_designer"],
            editableOnly: false,
        },
    };

    setup() {
        this.prom = null;
    }

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
