import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

const mainObjectRe = /website\.controller\.page\(((\d+,?)*)\)/;

export class ControllerPageListingLayoutOption extends BaseOptionComponent {
    static template = "website.ControllerPageListingLayoutOption";
    static selector = ".listing_layout_switcher";
    static editableOnly = false;
    static title = _t("Layout");
    static groups = ["website.group_website_designer"];
}

class ControllerPageListingLayoutOptionPlugin extends Plugin {
    static id = "controllerPageListingLayoutOption";
    static dependencies = ["builderActions"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [ControllerPageListingLayoutOption],
        builder_actions: {
            ListingLayoutAction,
        },
    };
}

export class ListingLayoutAction extends BuilderAction {
    static id = "listingLayout";
    setup() {
        this.reload = {};
        this.layout = undefined;
        this.resIds = undefined;
    }
    async prepare() {
        const mainObjectRepr = this.document.documentElement.getAttribute("data-main-object");
        const match = mainObjectRe.exec(mainObjectRepr);
        if (match && match[1]) {
            this.resIds = match[1].split(",").flatMap((e) => {
                if (!e) {
                    return [];
                }
                const id = parseInt(e);
                return id ? [id] : [];
            });
        }
        const results = await this.services.orm.read("website.controller.page", this.resIds, [
            "default_layout",
        ]);
        this.layout = results[0]["default_layout"];
    }
    getValue() {
        return this.layout;
    }
    isApplied({ value }) {
        return this.layout === value;
    }
    async apply({ editingElement: el, value }) {
        const params = {
            layout_mode: value,
            view_id: el.dataset.viewId,
        };
        // Save the default layout display, and set the layout for the current user
        await Promise.all([
            this.services.orm.write("website.controller.page", this.resIds, {
                default_layout: value,
            }),
            rpc("/website/save_session_layout_mode", params),
        ]);
    }
}

registry
    .category("website-plugins")
    .add(ControllerPageListingLayoutOptionPlugin.id, ControllerPageListingLayoutOptionPlugin);
