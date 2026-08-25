import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { generateGMapLink } from "@website/js/utils";

export class MapOptionPlugin extends Plugin {
    static id = "mapOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [".s_map"],
        builder_actions: {
            MapUpdateSrcAction,
        },
    };

    setup() {
        this.upgradeSnippets();
    }

    // TODO: Remove this method when data-vxml is reintroduced.
    upgradeSnippets() {
        // Ensure that all map snippets have the correct editable/not-editable classes
        // This is for pages which already existed before the plugin was created.
        const mapSnippetEls = this.document.querySelectorAll(".s_map");
        mapSnippetEls.forEach((mapSnippetEl) => {
            mapSnippetEl.classList.remove("o_not_editable");
            mapSnippetEl.dataset.vxml = "001";
            mapSnippetEl.querySelector(".map_container").classList.remove("o_not_editable");
            if (!mapSnippetEl.style.getPropertyValue("--GoogleMap-height")) {
                // Old map snippets used padding classes for the height. This
                // condition converts them into the CSS variable.
                const paddingClasses = [...mapSnippetEl.classList].filter((cls) =>
                    /^p(b|t)\d+$/.test(cls)
                );
                let mapHeight = 0;
                for (const cls of paddingClasses) {
                    mapHeight += parseInt(/\d+$/.exec(cls)[0]);
                    mapSnippetEl.classList.remove(cls);
                }
                mapSnippetEl.style.setProperty("--GoogleMap-height", `${mapHeight}px`);
            }
        });
    }
}

export class MapUpdateSrcAction extends BuilderAction {
    static id = "mapUpdateSrc";
    apply({ editingElement }) {
        const embedded = editingElement.querySelector(".s_map_embedded");

        if (editingElement.dataset.mapAddress) {
            const url = generateGMapLink(editingElement.dataset);
            if (url !== embedded.getAttribute("src")) {
                embedded.setAttribute("src", url);
            }
        } else {
            embedded.setAttribute("src", "about:blank");
        }
        embedded.classList.toggle("d-none", !editingElement.dataset.mapAddress);
        editingElement
            .querySelector(".missing_option_warning")
            .classList.toggle("d-none", !!editingElement.dataset.mapAddress);
    }
}

registry.category("website-plugins").add(MapOptionPlugin.id, MapOptionPlugin);
