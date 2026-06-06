import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class MapDescriptionPlugin extends Plugin {
    static id = "mapDescription";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            MapDescriptionAction,
        },
        content_not_editable_selectors: ".s_map, .s_google_map",
        content_editable_selectors: ":is(.s_map, .s_google_map) .description_content",
        // Prevent the overlay of `s_map` when clicking on the description
        // (which prevents future clicks in the description)
        has_overlay_options: {
            hasOption: (el) => el.matches(":is(.s_map, .s_google_map) .description"),
        },
    };

    setup() {
        // A click on the div containing the editable span may remove the focus
        // from the span, thus this handler forces the focus back in
        this.addDomListener(this.editable, "click", (ev) => {
            if (ev.detail === 1 && ev.target.matches(":is(.s_map, .s_google_map) .description")) {
                ev.target.querySelector(":scope > .description_content").focus();
            }
        });

        this.upgradeSnippets();
    }

    upgradeSnippets() {
        // Ensure the description's content is wrapped in an inline div which
        // is used to set the contenteditable=true
        // This is for pages which already existed before the wrapper existed
        this.document
            .querySelectorAll(":is(.s_map, .s_google_map) .description")
            .forEach((descriptionEl) => {
                if (!descriptionEl.querySelector(".description_content")) {
                    const descriptionContentEl = this.document.createElement("div");
                    descriptionContentEl.classList.add("description_content", "d-inline");
                    descriptionContentEl.replaceChildren(...descriptionEl.childNodes);
                    descriptionEl.classList.add("oe_unremovable");
                    descriptionEl.replaceChildren(descriptionContentEl);
                }
            });
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
