import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MapDescriptionPlugin extends Plugin {
    static id = "mapDescription";
    static dependencies = ["dom"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            MapDescriptionAction,
        },
        content_not_editable_selectors: ".s_map, .s_google_map",
        content_editable_selectors: ":is(.s_map, .s_google_map) .description",
        // Prevent the overlay of `s_map` when clicking on the description
        // (which prevents future clicks in the description)
        has_overlay_options: {
            hasOption: (el) => el.matches(":is(.s_map, .s_google_map) .description"),
        },
    };

    setup() {
        this.upgradeSnippets();
    }

    upgradeSnippets() {
        // Ensure the description's tag is `p`
        // This is for pages which already existed before, when it was a `div`
        this.document
            .querySelectorAll(":is(.s_map, .s_google_map) div.description")
            .forEach((oldEl) =>
                this.dependencies.dom.setTagName(oldEl, "p").classList.add("oe_unremovable")
            );
    }
}

export class MapDescriptionAction extends BuilderAction {
    static id = "mapDescription";
    static dependencies = ["builderOptions", "websiteBridge"];
    isApplied({ editingElement }) {
        return !!editingElement.querySelector(".description");
    }
    apply({ editingElement }) {
        const newEl = this.dependencies.websiteBridge.renderToElement("website.MapsDescription");
        editingElement.append(newEl);
        this.dependencies.builderOptions.setNextTarget(newEl);
    }
    clean({ editingElement }) {
        editingElement.querySelector(".description").remove();
    }
}

registry.category("website-plugins").add(MapDescriptionPlugin.id, MapDescriptionPlugin);
